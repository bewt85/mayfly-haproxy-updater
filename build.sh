#!/bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "Must be run as root.  Use \`sudo -E $0\` to keep the DOCKER_ACCOUNT_NAME variable accessible"
  exit 1
fi

PROJECT=haproxy_updater
DIR="$( cd "$( dirname $0 )" && pwd )"

if [[ ! -z $DOCKER_ACCOUNT_NAME ]]; then
  container_name="${DOCKER_ACCOUNT_NAME}/${PROJECT}"
else
  container_name="${PROJECT}"
fi

cd $DIR
if [[ ! $(git tag | grep -e "^release/") ]]; then
  echo 'Could not find any releases.  You can make some with `git tag release/<version_number> [commit reference]`'
fi

make_scripts_executable() {
  for file in $(find . -name "*.sh" -o -name "*.py" | xargs ls -l | awk '/^...-/ {print $NF}'); do
    echo "WARNING: '$file' appears to be a script but is not executable.  Updating permissions"
    chmod +x $file
  done
}

echo "Building ${container_name}:latest from $DIR"
make_scripts_executable
docker build -t ${container_name} $DIR

for version in $(git tag | awk '/release\// { sub(/^release\//,""); print }'); do
  cd $DIR
  TEMP_DIR=$(mktemp -d)
  git archive "release/${version}" > ${TEMP_DIR}/${PROJECT}.tar
  cd $TEMP_DIR
  tar xf ${TEMP_DIR}/${PROJECT}.tar
  echo "Building ${container_name}:${version} from $DIR"
  make_scripts_executable
  docker build -t ${container_name}:${version} $TEMP_DIR
  rm -r $TEMP_DIR
done
