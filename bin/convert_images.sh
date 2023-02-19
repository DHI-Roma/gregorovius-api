#!/bin/bash

IMAGE_PATH='./img/hd'
WEBP_PATH='./img/webp'

mkdir -p ${WEBP_PATH}

for file in ${IMAGE_PATH}/*; do
  echo "Converting ${file}"
  filename=$(basename -- "$file")
  filename="${filename%.*}"
  convert "${file}" -define webp:lossless=false "${WEBP_PATH}/${filename}.webp"
done
