proxyserver="domain:port"
proxydomain="domain"
proxyport="port"

#system wide
echo "http_proxy=http://$proxyserver/" >> /etc/environment
echo "https_proxy=http://$proxyserver/" >> /etc/environment
echo "ftp_proxy=http://$proxyserver/" >> /etc/environment
echo "no_proxy=localhost,127.0.0.1,localaddress,.localdomain.com" >> /etc/environment

#apt
echo "Acquire::http::proxy \"http://$proxyserver/\";" >> /etc/apt/apt.conf
echo "Acquire::ftp::proxy \"ftp://$proxyserver/\";" >> /etc/apt/apt.conf
echo "Acquire::https::proxy \"http://$proxyserver/\";" >> /etc/apt/apt.conf

#wget
echo "http_proxy=http://$proxyserver/" >> /etc/wgetrc
echo "https_proxy=http://$proxyserver/" >> /etc/wgetrc

#git
git config --global http.proxy http://$proxyserver
git config --global https.proxy http://$proxyserver

#nodejs
npm config set proxy http://proxyserver --global
npm config set https-proxy http://proxyserver --global

#gradle
echo "systemProp.http.proxyHost=$proxydomain" >> ~/.gradle.properties
echo "systemProp.http.proxyPort=$proxyport" >> ~/.gradle.properties
echo "systemProp.https.proxyHost=$proxydomain" >> ~/.gradle.properties
echo "systemProp.https.proxyPort=$proxyport" >> ~/.gradle.properties
