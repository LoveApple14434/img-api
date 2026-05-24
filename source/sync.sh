#!/bin/bash

rm ./img/*
cp -v ~/mnt/N5105/download/pics/photography/* ./img/
bash ./zip.sh
rm ../image_cache.json

