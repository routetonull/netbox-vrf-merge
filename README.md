# Netbox VRF merger

Read data from two NetBox VRFs, merge to third VRF.

## Data and credentials

Credentials, VRF ID for sources and destination must be provided in **.env** file

## Install requirements

```
python -m pip install -r requirements.txt
```

## Usage

Verify the destination VRF exists (it will not be created by the script). *Note to self: add target VRF existence check. Permit prefix overlap on target VRF, do not set "enforce unique".*

Execute:

```
./nb-merge-vrf.py
```

Or use a virtual-end (strongly recommended) and execute with:

```
./run.sh
```