# Installation #
Installation is rather easy. First you need to install ctypeslib, a way to do it could be:

```
sudo easy_install ctypeslib
```

Then you need to get our source tree and install it
```
hg clone https://cusepy.googlecode.com/hg/ cusepy 
cd cusepy
sudo python setup.py install
```

# Testing #
`cuse_example.py` will create a character device which will push all what it gets into it's own buffer, and then return it back when you try reading it.

You can check if cusepy is working by running cuse\_example.py
```
cd cusepy
mknod -m 777 /dev/ttyTEST c 200 1
sudo python cuse_example.py ttyTEST -d debug
```

Now you can write something to /dev/ttyTEST in a new shell
```
echo "Hello world!" > /dev/ttyTEST
```

And get it back
```
cat /dev/ttyTEST
```