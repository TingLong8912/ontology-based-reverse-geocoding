docker build -t test image
docker run \
  -it --rm \
  -p 30000:80 \
  -v $PWD/src/main.py \
  test
