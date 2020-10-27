#!/bin/sh

cd $1

read -p "Download SNLI dataset? y/[n] " ans
ans=${ans:-no}
if [ $ans = 'y' ]; then
    if [ ! -f snli_1.0.zip ]; then
        wget https://nlp.stanford.edu/projects/snli/snli_1.0.zip
    fi
    unzip snli_1.0.zip
    rm -fr __MACOSX/
fi

read -p "Downloading Flickr30K images and captions? y/[n] " ans
ans=${ans:-no}
if [ $ans = 'y' ]; then
    #mkdir ~/.kaggle
    #echo "Download and place your Kaggle API token in ~/.kaggle/kaggle.json beforehand"
    #pip install kaggle
    #kaggle datasets download -d hsankesara/flickr-image-dataset
    #unzip flickr-image-dataset.zip
    #ln -sf flickr30k_images/flickr30k_images images
    #ln -sf flickr30k_images/results.csv
    # rm flickr-image-dataset.zip

    if [ ! -f flickr30k_images.tar.gz ]; then
        # Credits to BAN: https://github.com/jnhwkim/ban-vqa
        wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://drive.google.com/uc?export=download&id=0B_PL6p-5reUAZEM4MmRQQ2VVSlk' -O tmp.html
        wget --load-cookies /tmp/cookies.txt "https://drive.google.com/uc?export=download&confirm=$(cat tmp.html | sed -En 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=0B_PL6p-5reUAZEM4MmRQQ2VVSlk" -O flickr30k_images.tar.gz
        rm -rf /tmp/cookies.txt tmp.html
    fi

    tar zxf flickr30k_images.tar.gz
    ln -sf flickr30k_images images
    ln -sf results_20130124.token results.tsv
    rm flickr30k_images.tar.gz
fi

<<COMMENT
read -p "Downloading Flickr30K features from Faster R-CNN trained on Visual Genome? y/[n] " ans
ans=${ans:-no}
if [ $ans = 'y' ]; then
    if [ ! -f flickr30k_features.zip ]; then
        # Credits to BAN: https://github.com/jnhwkim/ban-vqa
        wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://drive.google.com/uc?export=download&id=11OD_qq7ITBarJwWZfi0bWIRw3HPEaHwE' -O tmp.html
        wget --load-cookies /tmp/cookies.txt "https://drive.google.com/uc?export=download&confirm=$(cat tmp.html | sed -En 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=11OD_qq7ITBarJwWZfi0bWIRw3HPEaHwE" -O flickr30k_features.zip
        rm -rf /tmp/cookies.txt tmp.html
    fi
    mkdir -p features
    unzip flickr30k_features.zip -d features/resnet101-faster-rcnn-vg-100-2048
    # rm flickr30k_features.zip
fi
COMMENT

echo "Downloading Flickr30K Entities..."
git clone https://github.com/BryanPlummer/flickr30k_entities.git repo
mv repo/*.txt .
mv repo/*.py .
mv repo/*.zip .
rm -fr repo

unzip annotations.zip
rm annotations.zip