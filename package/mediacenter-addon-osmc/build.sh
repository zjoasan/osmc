#!/bin/bash
# (c) 2014-2015 Sam Nazarko
# email@samnazarko.co.uk

. ../common.sh

echo -e "Building package mediacenter-addon-osmc"
make clean
mkdir -p files/usr/share/kodi/addons
cp -ar src/* files/usr/share/kodi/addons

# Windows the first-boot walkthrough can open get an alias that no skin ships,
# so they keep OSMC's original look there (see osmccommon/osmc_skin.py)
for name in script-myosmc-network
do
	for xml in files/usr/share/kodi/addons/*/resources/skins/Default/1080i/$name.xml
	do
		[ -f "$xml" ] && cp "$xml" "${xml%.xml}-default.xml"
	done
done

# 720p skins size their fonts in 720 coordinates, so each MyOSMC window gets a
# twin using the smaller osmc_addon_720_* fonts (see osmccommon/osmc_skin.py)
for xml in files/usr/share/kodi/addons/*/resources/skins/Default/1080i/script-myosmc*.xml
do
	case "$xml" in *-720.xml) continue ;; esac
	sed -E 's/osmc_addon_(XLarge|Large|Med|Small|XSmall|font13)</osmc_addon_720_\1</g' "$xml" > "${xml%.xml}-720.xml"
done

dpkg_build files/ mediacenter-addon-osmc.deb
