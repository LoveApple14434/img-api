#!/bin/bash

rm ./img-zipped/*
for img in ./img/*.jpg; do
	filename=$(basename "$img")
	ffmpeg -i "$img" -vf scale=640:-1 "./img-zipped/$filename"
done
