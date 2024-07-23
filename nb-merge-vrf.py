#!/usr/bin/env python
from dataclasses import dataclass
from typing import Any, List
from dotenv import load_dotenv
from loguru import logger
import os
from ipaddress import ip_network
from requests.packages import urllib3
from requests import Session
import sys
import pynetbox

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


__author__ = "Gian Paolo Boarina"
__copyright__ = "Copyright (C) 2021 Gian Paolo Boarina"
__license__ = "©2021. This work is openly licensed via CC BY-SA 4.0"


@dataclass
class Data:
    """
    load data from dotenv file
    """
    try:
        load_dotenv()
    except:
        logger.exception("Failed to load dotenv")
        sys.exit()
    nbserver: str = os.getenv("NB_SERVER", "")
    nbtoken: str = os.getenv("NB_TOKEN", "")
    vrfsource1 : str = os.getenv("VRF1", "0")
    vrfsource2 : str = os.getenv("VRF2", "0")
    vrftarget : str = os.getenv("VRF3", "0")
    dry :bool = bool(int(os.getenv("DRY", 1))) # dry run flag, default is true


def __nbconnect(d):
    """
    connect to NetBox
    """
    session = Session()
    session.verify = False
    if "http" not in d.nbserver:
        nburl = f"https://{d.nbserver}"
    else:
        nburl = d.nbserver
    try:
        nb = pynetbox.api(url=nburl, token=d.nbtoken)
    except:
        logger.exception(f"Cannot connect to NetBox server {d.nbserver}")
    nb.http_session = session
    return nb


def __clearMerged(nb,destinationVRF:int=0):
    """
    deletes all the prefixes of the destination VRF
    """
    
    # adapt range to destination VRF range, as a safety mechanism to prevento errors
    assert int(destinationVRF) in [0,999] ,f"Destination VRF {destinationVRF} not in allowed range"
    
    nbprefix_merged = nb.ipam.prefixes.filter(vrf_id=destinationVRF, limit=0)
    total = len(nbprefix_merged)
    logger.debug(f"Total prefixes to be deleted: {total}")
    count = 1
    repetitions = 0
    while len(nbprefix_merged) > 0 and repetitions < 20:    
        repetitions +=1 # loop prevention
        for prefix in nbprefix_merged:
            prefix.delete()
            logger.debug(f"Deleted prefix {count}/{total} prefix {prefix.prefix}")
            count+=1
        nbprefix_merged = nb.ipam.prefixes.filter(vrf_id=destinationVRF, limit=0)
    if repetitions == 10:
        logger.exception(f"Something went wrong with clearing, too many repetitions")
    return total


def __merge_vrf(nb=False, sourceVRF:int=0, destinationVRF:int=0, newtags:List=[]):
    '''
    merge source vrf to destination vrf
    append newtags to the prefix if provided
    '''

    # adapt range to source VRF range, as a safety mechanism to prevento errors
    assert int(sourceVRF) in [0,999] ,f"Destination VRF {sourceVRF} not in allowed range"
    # adapt range to destination VRF range, as a safety mechanism to prevento errors
    assert int(destinationVRF) in [0,999] ,f"Destination VRF {destinationVRF} not in allowed range"

    logger.debug(f"Adding source prefixes from VRF {sourceVRF} to destination VRF {destinationVRF}. Will append tags: {newtags}")
    nbprefix_source = nb.ipam.prefixes.filter(vrf_id=sourceVRF) 
    count = 1
    total = len(nbprefix_source)
    logger.info(f"Source prefixes: {total}")
    for prefix in nbprefix_source:
        p = prefix.serialize()     
        p.get('tags').extend(newtags) # copy tags and append source VRF tag                 
        
        # new prefix to be pushed
        newprefix = {
            'prefix' : p.get('prefix'),
            'site' :  p.get('site'),
            'vrf' : destinationVRF,
            'vlan' :  p.get('vlan'),
            'status' :  p.get('status'),
            'role' : p.get('role'),
            'is_pool': False,
            'description' : p.get('description'),
            "tags": p.get('tags'), # copy tags and append source VRF tag
        }
        
        try:
            nb.ipam.prefixes.create(**newprefix)
        except:
            logger.exception(f"failed to create prefix {newprefix.get('prefix')}")
        logger.info(f"Prefixes merged {count}/{total}")
        count+=1
    return total


def main():
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True)
    logger.add("run.log", retention="180 days", rotation="30 days")
    
    logger.info(f"Loading data from .env file")
    d = Data() # load data from .env file

    logger.info(f"Connecting to netbox")
    nb = __nbconnect(d)

    logger.info(f"Deleting all existing merged prefixes from VRF {d.vrftarget}")
    cleared = __clearMerged(nb,d.vrftarget)
    logger.info(f"Total cleared prefixes: {cleared}")

    logger.info(f"Merging VRF 1 to target VRF")
    total = __merge_vrf(nb,d.vrfsource1,d.vrftarget,[])

    logger.info(f"Merging VRF 2 to target VRF")
    total += __merge_vrf(nb,d.vrfsource2,d.vrftarget,[])

    logger.info(f"Total merged prefixes: {total}")

    # double check just in case    
    total_in_VRF = len(nb.ipam.prefixes.filter(vrf_id=d.vrftarget))
    if total != total_in_VRF:
        logger.error(f"Merged VRF {total_in_VRF} no match expected {total}")
    
if __name__ == "__main__":
    main()
