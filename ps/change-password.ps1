winrm quickconfig
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Restart-Service WinRM

$pcs="7840hs","7640hs","4700u"
$pwd=ConvertTo-SecureString "tianlongbabuQ!1" -AsPlainText -Force

Invoke-Command -ComputerName $pcs -ScriptBlock {
    Set-LocalUser -Name "bx" -Password $using:pwd
    Set-LocalUser -Name "fz" -Password $using:pwd
}