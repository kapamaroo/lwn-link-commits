#!/bin/bash

diff page.html testpage.html \
     -y -W $(tput cols) \
     --ignore-space-change \
     --ignore-case \
     --suppress-common-lines \
    | less
