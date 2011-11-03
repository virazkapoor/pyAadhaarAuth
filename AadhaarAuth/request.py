#!/usr/bin/env python
#
#Copyright (C) 2011 by Venkata Pingali (pingali@gmail.com) & TCS 
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

#
#<?xml version="1.0"?> 
#<Auth xmlns="http://www.uidai.gov.in/authentication/uid-auth-request/1.0" 
#      ver="1.5" tid="public" ac="public" sa="public" 
#      lk="MKg8njN6O+QRUmYF+TrbBUCqlrCnbN/Ns6hYbnnaOk99e5UGNhhE/xQ=" uid="999999990019" 
#      txn="GEO.11051880"> 
#      <Skey ci="20131003">Nc6DrZKFk...
#      </Skey> 
#      <Uses otp="n" pin="n" bio="n" pa="n" pfa="n" pi="y" /> 
#      <Data>YOn05vg5qMwElULpEmdiH0j6rM...
#      </Data> 
#      <Hmac>xy+JPoVN9dsWVm4YPZFwhVBKcUzzCTVvAxikT6BT5EcPgzX2JkLFDls+kLoNMpWe 
#      </Hmac> 
#</Auth> 
#

import sys
sys.path.append("lib") 

#import libxml2
from lxml import etree, objectify 

import dumper 
import hashlib 
import hmac
from config import Config 
import traceback 
import base64 
import random 
from datetime import datetime
from M2Crypto import Rand 

from crypt import AuthCrypt 
from signature import AuthRequestSignature
from validate import AuthValidate

__author__ = "Venkata Pingali"
__copyright__ = "Copyright 2011,Venkata Pingali and TCS" 
__credits__ = ["UIDAI", "MindTree", "GeoDesic", "Viral Shah"] 
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Venkata Pingali"
__email__ = "pingali@gmail.com"
__status__ = "Pre-release"


"""
This module implements the authentication request class. We could
potentially move the authentication response class to this module as
well.
"""
class AuthRequest():

    """
    Base class to parse, validate, and generate auth requests going to
    the server. Mostly it will be used in the generate mode. The aim
    is to simplify writing applications around the auth request. We
    could potentially use this with AppEngine and Django that are
    python-based. This interface supports only v1.5 and public AuAs 
    """

    # Constants 
    data_xmlns = "http://www.uidai.gov.in/authentication/uid-auth-request-data/1.0"
    request_xmlns="http://www.uidai.gov.in/authentication/uid-auth-request/1.0"
    
    def __init__(self, cfg=None, biometrics=False, uid="", 
                 tid="public", lk="", txn=""):
        """
        Constructor of AuthRequest (see source for more details). 
        
        Set the configuration, flag to indicate whether this is
        biometrics or demographics, and additional addtributes
             
        cfg: Config object (see fixtures/auth.cfg example) (default: None)
        biometrics: Whether this request is for biometrics or not (default: False) 
        uid: uid of the requestor (default="") 
        tid: terminal id (default: "public") 
        txn: transaction id (default: "") 
        lk: License key (if not specified, then config file entry is used) (default: "") 

        """
        self._cfg = cfg 
        self._biometrics = biometrics
        self._pidxml_biometrics = None
        self._pidxml_demographics = None 
        self._session_key = None

        self._tid = tid
        self._lk = lk
        if (self._lk == ""): 
            self._lk = cfg.common.license_key
            
        self._ac = "public"
        self._ver = "1.5" 
        self._sa = "public" 
        self._uid = uid
        self._txn = txn 
        self._skey = { 
            '_ci': None, 
            '_text': None}
        self._uses  = { 
            '_otp': "n", 
            '_pin': "n",
            '_bio': "n", 
            '_pfa': "n",
            '_pi': "n",
            '_pa': "n",
            }
        self._hmac = ""
        self._data = ""

    def validate(self): 
        """
        Check for whether the data is complete enough to be able to 
        generate an authentication request. 
        """
        if ((self._skey['_ci'] == None) or (self._skey['_text'] == None)):
            raise Exception("Invalid Skey ci or text")
        
        if (self._pidxml_demographics == None and 
            self._pidxml_biometrics == None):
            raise Exception("Payload (demographics/biometics) not set") 

    
    def set_txn(self, txn=""):
        """
        Update the transaction information
        """
        if (txn == ""):
            self._txn = random.randint(2**15, 2**16-1)

    def set_skey(self):
        """
        Generate the session and set the Skey parameters. 
        """
        a = AuthCrypt(cfg.request.uid_cert_path, None) 
        when = a.x509_get_cert_expiry() #Jun 28 04:40:44 2012 GMT
        expiry = datetime.strptime(when, "%b %d %H:%M:%S %Y %Z")
        self._session_key = Rand.rand_bytes(self._cfg.common.rsa_key_len) 
        print "session_key (encoded) = ", base64.b64encode(self._session_key)
        self._skey['_ci'] = expiry.strftime("%Y%m%d")
        self._skey['_text'] = a.x509_encrypt(self._session_key)

    def get_skey(self):
        """
        Return the Skey 
        """
        return { 
            'ci': self._skey['_ci'],
            'text': self._skey['_text'],
            }

    def set_data(self):
        """
        Set the content of the data element using the pidxml
        generated and stored as part of this class
        """
        if self._biometrics:
            data = self._pidxml_biometrics
        else:
            data = self._pidxml_demographics                

        x = AuthCrypt() 
        self._data = base64.b64encode(x.aes_encrypt(key=self._session_key, msg=data))
        print "Data = ", self._data

    def get_data(self):
        return self._data 

    def set_hmac(self): 
        """
        Computes the hmac. Not working yet.
        """
        if self._biometrics:
            data = self._pidxml_biometrics
        else:
            data = self._pidxml_demographics                
        
        sha256_data = hashlib.sha256(data).hexdigest()
        print "Sha256 data = ", sha256_data

        x = AuthCrypt() 
        self._hmac = x.aes_encrypt(key=self._session_key, msg=sha256_data)
        print "Hmac = ", self._hmac 
        return self._hmac 

    def get_hmac(self):
        return self._hmac 
        
    def set_pidxml_biometrics(self, datatype="FMR", 
                              data=None, ts=None):
        
        """
        Generate the biometrics XML payload. Supports only FMR for now
        """ 

        if (datatype != "FMR"): 
            raise Exception("Non FMR biometrics not supported") 
        
        if (data == None): 
            raise Exception("Data for biometrics inclusion is missing") 

        self._uses['_bio'] = "y"
        self._uses['_bt'] = "FMR"
        
        # the biometrics may be collected somewhere else and the
        # timestamp may be set there. If it not set, set it to 
        # local time 
        if ts == None:
            ts = Datetime.utcnow() 

        root = etree.Element('Pid', 
                             xmlns=self.data_xmlns,
                             ts=ts.strftime("%Y-%m-%dT%H:%M:%S"),
                             ver="1.0")
        bios = etree.SubElement(root, "Bios")
        bio=etree.SubElement(bios, "Bio", type="FMR")
        bio.text = data 
        doc = etree.ElementTree(root) 
        
        # Update internal state 
        self._pidxml_biometrics = etree.tostring(doc,pretty_print=True)
        
        return True 


    def set_pidxml_demographics(self, datatype="Name", 
                                data=None, ts=None):
        """
        Generate the demographics XML payload.
        """

        if (datatype != "Name" or data == None):
            raise Exception("Does not support demographic checks other than Name") 
        
        self._uses['_pi'] = "y" 
        
        if ts == None:
            ts = datetime.utcnow() 

        # construct the demographics xml 
        root = etree.Element('Pid', 
                             xmlns=self.data_xmlns, 
                             ts=ts.strftime("%Y-%m-%dT%H:%M:%S"),
                             ver="1.0")
        demo = etree.SubElement(root, "Demo")
        pi=etree.SubElement(demo, "Pi", ms="E", name=data)
        doc = etree.ElementTree(root) 
        
        # update the internal state 
        self._pidxml_demographics = etree.tostring(doc,pretty_print=True)
        return True 

    def tostring(self):
        """
        Generate the XML text that must be sent across to the uid
        client.
        """
        self.validate()

        root = etree.Element('Auth', 
                                xmlns=self.request_xmlns,
                                ver=self._ver,
                                tid=self._tid, 
                                ac=self._ac, 
                                sa=self._sa,
                                txn = self._txn,
                                uid = self._uid,
                                lk=self._lk
                                )
        skey = etree.SubElement(root, "Skey", ci=self._skey['_ci'])
        skey.text = base64.b64encode(self._skey['_text'])
        
        uses = etree.SubElement(root, "Uses", 
                                otp=self._uses['_otp'],
                                pin=self._uses['_pin'],
                                bio=self._uses['_bio'],
                                pfa=self._uses['_pfa'],
                                pi=self._uses['_pi'],
                                pa=self._uses['_pa'])
        
        data = etree.SubElement(root, "Data")
        data.text = self._data
        hmac = etree.SubElement(root, "Hmac")
        hmac.text = self._hmac

        doc = etree.ElementTree(root) 
        return ("<?xml version=\"1.0\"?>\n%s" %(etree.tostring(doc, pretty_print=True)))

        
if __name__ == '__main__':
    
    cfg = Config('fixtures/auth.cfg') 
    x = AuthRequest(cfg, uid="123412341237")
    x.set_skey() 
    x.set_pidxml_demographics(data="KKKK")
    x.set_data()
    x.set_hmac() 
    xml = x.tostring() 
    
    print "XML = ", xml

    v = AuthValidate(cfg.xsd.request) 
    res = v.validate(xml, is_file=False, signed=False)
    if (res == False): 
        print "Invalid XML generated" 

    tmpfile='/tmp/xxxx'
    signed_tmpfile = tmpfile + ".sig" 

    fp = file(tmpfile, 'w')
    fp.write(xml) 
    fp.close() 
    print "Have written tmp file", tmpfile 

    sig = AuthRequestSignature() 
    sig.init_xmlsec() 
    res = sig.sign_file(tmpfile, 
                      cfg.request.local_pkcs_path, 
                      cfg.request.pkcs_password)
    sig.shutdown_xmlsec() 

    print "Result of signing ", res
    
    res = v.validate(signed_tmpfile, is_file=True, signed=True)
    
    print "Result = ", res 