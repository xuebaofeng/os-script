SET "USERNAME=fz"
SET "PASSWORD=prqnoQ!1"

:: 1. 创建用户
net user %USERNAME% %PASSWORD% /add

:: 2. 启用用户
net user %USERNAME% /active:yes

:: 3. （可选）加入管理员组
net localgroup Administrators %USERNAME% /add
