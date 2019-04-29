pkgname='task-gmail-sync'
pkgver='0.1'
pkgrel='1'
arch=('any')
depends=("python"
         "python-taskw"
         "python-google-api-python-client"
         "python-google-auth-httplib2"
         "python-google-auth-oauthlib"
         "python-xdg")

source=("task_gmail_sync.py")
sha256sums=('bea7098204c553c1236461e704825317c0837b8eebee758bf7489c0f88e81011')


package() {
    mkdir -p $pkgdir/usr/bin
    mkdir -p $pkgdir/etc/task-gmail-sync
    cp task_gmail_sync.py $pkgdir/usr/bin
}
