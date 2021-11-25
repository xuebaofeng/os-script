sudo mkdir -p /shared/jellyfin/config
sudo mkdir -p /shared/jellyfin/cache

docker rm /jellyfin
docker run -d \
 --name jellyfin \
 --net=host \
 --volume /shared/jellyfin/config:/config \
 --volume /shared/jellyfin/cache:/cache \
 --mount type=bind,source=/shared/media,target=/media \
 --restart=unless-stopped \
 jellyfin/jellyfin