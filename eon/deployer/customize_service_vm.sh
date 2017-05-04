#!/bin/bash
#
# (c) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#.

export DEPLOY_IP="%s"
export DEPLOY_VLAN="%s"
export DEPLOY_NETMASK="%s"
export DEPLOY_GATEWAY="%s"
export DEPLOYER_INTERFACE="%s"
export USER="%s"
export DEPLOY_NODE_IP="%s"
export PCI_SLOTS="%s"
export ETH2MAC="%s"
export NUM_IFS="%s"
export TEMP_SSH_KEY="%s"

if [ -z "$DEPLOY_VLAN" ]; then
    DEPLOYER_IF=$DEPLOYER_INTERFACE
else
    DEPLOYER_IF="vlan"$DEPLOY_VLAN
fi

RULES_FILE=/etc/udev/rules.d/70-persistent-net.rules
TEMP_INTERFACE=/etc/network/interfaces.new


update_interfaces () {
    echo "Creating conf interface ..."
    echo "auto $DEPLOYER_IF" >> $TEMP_INTERFACE
    if [ -z "$DEPLOY_IP" ]; then
        echo "iface $DEPLOYER_IF inet dhcp" >> $TEMP_INTERFACE
        echo "    configpath /etc/dhcp/dhclient.$DEPLOYER_IF.conf" >> $TEMP_INTERFACE
    else
        echo "iface $DEPLOYER_IF inet static" >> $TEMP_INTERFACE
        echo "    address $DEPLOY_IP" >> $TEMP_INTERFACE
        echo "    netmask $DEPLOY_NETMASK" >> $TEMP_INTERFACE
        if [ "$DEPLOY_VLAN" ]; then
            echo 8021q >> /etc/modules
            /sbin/modprobe 8021q
            echo "    vlan-raw-device $DEPLOYER_INTERFACE" >> $TEMP_INTERFACE
        fi
        echo "    up ip route add $DEPLOY_NODE_IP/32 via $DEPLOY_GATEWAY" >> $TEMP_INTERFACE
        echo "    down ip route delete $DEPLOY_NODE_IP/32" >> $TEMP_INTERFACE
    fi
    if [ "$DEPLOY_VLAN" ]; then
        if [ "$DEPLOYER_INTERFACE" != "eth0" ]; then
            echo "" > /etc/network/interfaces.d/eth0
        fi
        echo "iface $DEPLOYER_INTERFACE inet manual" > /etc/network/interfaces.d/$DEPLOYER_INTERFACE
        echo "    pre-up ifconfig \$IFACE up" >> /etc/network/interfaces.d/$DEPLOYER_INTERFACE
        echo "    post-down ifconfig \$IFACE down" >> /etc/network/interfaces.d/$DEPLOYER_INTERFACE
    fi
}

bring_down_interface () {
    echo "Bringing down $1"
    /sbin/ifdown $1 || true
}

bring_up_interface () {
    echo "Bringing up $1"
    /sbin/ifup $1 || true
}

request_dhcp_ip_for_interface () {
    local max_retries=3
    local retries=0
    INTERFACE_IP=""
    while [ $retries -lt $max_retries ]
    do
        /sbin/dhclient -cf /etc/dhcp/dhclient.$1.conf $1
        if [ $? -eq 0 ]; then
            INTERFACE_IP=`/sbin/ifconfig $1 | grep 'inet addr' | awk -F: '{print $2}' | awk '{print $1}'`
        fi
        if [ -z "$INTERFACE_IP" ];
        then
            retries=`expr $retries  + 1`
        else
            break
        fi
    done
}

add_rules() {
    RULES='SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{address}=="'$1'", ATTR{type}=="1", KERNEL=="eth*", NAME="'$2'"'
    echo "" >> $RULES_FILE
    echo "Adding rule $RULES"
    echo $RULES >> $RULES_FILE
}

reload_drivers() {
    modprobe -r vmxnet3
    service udev restart
    modprobe vmxnet3
}

rearrange_vmxnet3_interfaces() {
    # Rearrange vmxnet interfaces. Occurs generally when adapters are more than 4/5
    IFS=","
    for item in $ETH2MAC
        do
            ETH=`echo $item | cut -d '=' -f1`
            MAC=`echo $item | cut -d '=' -f2`
            add_rules $MAC $ETH
        done
    unset IFS
    reload_drivers
}

update_presistent_rules () {
   echo "Renaming Interface $1 to $2"
   sed -i "s/, NAME=\"$1\"/, NAME=\"$2\"/g" $RULES_FILE

   num_ifs=$(($NUM_IFS-1))
   delm=`echo -n $2 | tail -c 1`
   entries=$(($num_ifs-delm))
   if [ $entries -gt 0 ];
   then
       target_eth=$2
       for i in $(seq 1 $entries)
       do
           current_eth=$target_eth
           target_eth=eth$(($delm+$i))
           MAC=`ip link show $current_eth | awk '/ether/ {print $2}'`
           add_rules $MAC $target_eth
       done
   fi
}

rename_interfaces () {
    echo "Interface $1 with slot id $2"
    IFS=$'\n'
    BUS_ID=`lspci -vvv | tac |sed -n "/Physical Slot: $2/,+2p" | tac | awk '{print $1}'`
    BUS_ID=`echo $BUS_ID | cut -d' ' -f1`
    echo "BUS_ID is $BUS_ID"
    IFNAMES=`ifconfig -a | less | grep eth | cut -d' ' -f1 `
    CURRENT_ETH=""
    for i in $IFNAMES
    do
        bus_id=`ethtool -i $i | grep bus-info | awk -F':' '{print $3":" $4}'`
        if [ "$BUS_ID" = "$bus_id" ]; then
            CURRENT_ETH=$i
            break
        fi
    done
    unset IFS
    update_presistent_rules $CURRENT_ETH $1
}

rearrange_pci_interfaces () {
    IFS=","
    for val in $PCI_SLOTS
        do
            eth=`echo $val | cut -d ':' -f1`
            slot=`echo $val | cut -d ':' -f2`
            echo "Invoking rearrange function with eth=$eth & slot=$slot"
            rename_interfaces $eth $slot
        done
    unset IFS
}

create_user () {
    HOME=/home/$USER
    SSH_DIR=$HOME/.ssh
    if id -u "$USER" >/dev/null 2>&1; then
        echo "User $USER already exists"
    else
        echo "User $USER does not exist. Will create the user."
        # Create user and add entry in sudoers
        SUDOERS=/etc/sudoers.d/$USER
        su -c "/usr/sbin/groupadd $USER"
        su -c "/usr/sbin/useradd $USER -s /bin/bash -d $HOME -m -g $USER"
        echo "$USER ALL=(ALL) NOPASSWD:ALL" >> $SUDOERS
        chmod 440 $SUDOERS
    fi
}

create_and_configure_ssh() {
    # Configure password less ssh for user
    if [ ! -d $SSH_DIR ]; then
        echo "Creating $SSH_DIR directory"
        mkdir $SSH_DIR
        chmod 700 $SSH_DIR
    fi

    echo "Giving permission to SSH directory and files"
    cat $TEMP_SSH_KEY >> $SSH_DIR/authorized_keys
    chmod 640 $SSH_DIR/authorized_keys
    chown -R $USER $SSH_DIR
    chgrp -R $USER $SSH_DIR
    rm $TEMP_SSH_KEY

    # Disable password base ssh
    echo "Disabling password based SSH authentication and restarting SSH service"
    sed -i "s/^#PasswordAuthentication yes/PasswordAuthentication no/" /etc/ssh/sshd_config
    echo "UseDNS no" >> /etc/ssh/sshd_config
    service ssh restart
}

############################## PROGRAM STARTS FROM HERE #####################################
# Bring down deployer interface
bring_down_interface $DEPLOYER_IF

# Configure the deployer interface
update_interfaces

mv $TEMP_INTERFACE /etc/network/interfaces.d/$DEPLOYER_IF

# Rearrange vmxnet3 interfaces
rearrange_vmxnet3_interfaces

# Rearrange PCI Passthrough and other interfaces if provided
if [ "$PCI_SLOTS" ]; then
    rearrange_pci_interfaces
fi

# Clear default resolv.conf contents
echo "" > /etc/resolv.conf

if [ -z "$DEPLOY_IP" ];
then
    request_dhcp_ip_for_interface $DEPLOYER_IF
fi

bring_up_interface $DEPLOYER_IF

# Create user if not exists
create_user

# Create and configure ssh for user
create_and_configure_ssh

# Cleanup
echo "Deleting the customization script"
rm -- "$0"

echo "Guest OS customization complete !"

sync
sync
sync

############################## PROGRAM ENDS HERE #####################################
