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


`$logfile = Join-Path -Path $($env:LOCALAPPDATA) -ChildPath "\Temp\activation`$(get-date -format `"yyyyMMdd_hhmmsstt`").log"

function logInfo(`$string)
{
   "INFO:"+`$string | out-file -Filepath `$logfile -append
}

function logError(`$string)
{
   "ERROR:"+`$string | out-file -Filepath `$logfile -append
}



<#
.DESCRIPTION
Checks for MSiSCSI service state and returns boolean
#>
Function CheckiSCSIInitiatorService{
  `$retval = `$false
  logInfo "Checking for MS iSCSI initiator service state"
  `$iSCSIserviceState = (Get-WmiObject -Class 'Win32_Service' -Filter "Name='MSiSCSI'").State
  if (`$iSCSIserviceState.Equals('Running')){
    logInfo "MS iSCSI initiator service is running in the hyperV host"
    `$retval = `$true
  } else{
    logError "MS iSCSI initiator service is not running in the hyperV host"
  }
  return `$retval
}

<#
.DESCRIPTION
Checks for Compute HOSTNAME less than 15 characters.
#>
Function CheckHostName{
  `$retval = `$false
  logInfo "Check if hostname and Win32_ComputerSystem name are same."
  `$computerName = (Get-WmiObject -Class 'Win32_ComputerSystem').Name
  `$hostName = hostname.exe
  `$validName = [string]::Compare(`$hostName, `$computerName, `$True)

  if (`$validName -eq 0){
    logInfo "Hostname and Win32_ComputerSystem name are same."
    `$retval = `$true
  } else{
    logError "Hostname and Win32_ComputerSystem name are different. Make sure that host name is set to less than 15 characters."
  }
  return `$retval
}


`$VmCount = `$(get-vm).Count
logInfo "Queried virtual machines running successfully"
`$OsVersion = [System.Environment]::OSVersion.Version
`$OsEdition = @{}
`$OsEdition.Add('name',`$(gwmi win32_operatingsystem).caption)
`$OsEdition.Add('number',`$(gwmi win32_operatingsystem).OperatingSystemSKU)
logInfo "Queried hyperv version details successfully"
`$HostName = hostname

`$hosts_file_configured = `$false
`$iSCSIserviceState = CheckiSCSIInitiatorService
`$checkHostName = CheckHostName
`$IPAddresses = @(`$(Get-NetIPAddress -AddressFamily IPv4).IPAddress)

`$data = @{
          "vm_count" = `$VmCount;
          "os_version" = `$OsVersion;
          "os_edition" = `$OsEdition;
          "hostname" = `$HostName;
          "iSCSI_initiator_service_state" = `$iSCSIserviceState;
          "ipaddresses" = `$IPAddresses
          "valid_compute_name" = `$checkHostName
         }

`$hyperv_data = ConvertTo-Json -InputObject `$data
return `$hyperv_data
