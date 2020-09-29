from Tims3xIO import *
import pdb
import re
import xml.etree.ElementTree as ET
import sys, getopt
import os
import argparse
import logging

logger = None

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--show-log', action='store_true', help='Prints log to stdout')
parser.add_argument('-l', '--log', type=str, required=False, default=os.devnull, help='Provide filename to store log')
parser.add_argument('-results_xml', type=str, required=True, help='Provide Results xml filepath')
parser.add_argument('-folder_id', type=str, required=True, help='Provide folder id for uploading results')


args = parser.parse_args()

if args.log != None:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(processName)-12s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=args.log,
                        filemode='w')
    logger = logging.getLogger('')
    if args.show_log:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('\r%(name)-12s: %(levelname)-8s %(message)s'))
        logger.addHandler(console)


directory = "C:\Users\hclqa\workspace\HCL_automation_11May\Reports"
#report_dir = max([os.path.join(directory,d) for d in os.listdir(directory)], key=os.path.getmtime)
#print report_dir

print "Executing tims.py"
build_number = 0
sys_proxy = None

tims_id = args.folder_id
#tims_id="Tps4525175f"

if sys_proxy == None:
    sys_proxy = "http://72.163.217.103:80"

start_xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Tims
    xsi:schemaLocation="http://tims.cisco.com/namespace http://tims.cisco.com/xsd/Tims.xsd"
    xmlns="http://tims.cisco.com/namespace"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xlink="http://www.w3.org/1999/xlink">
    <Credential user="shuchugh" token="090062203D5018003778014400140000"/>
    """
print "tims_id:", tims_id
filler_xml = """<Result >
        <Title><![CDATA[%s]]></Title>
        <FolderID xlink:href="http://tims.cisco.com/xml/"""+tims_id+"""/entity.SVC">"""+tims_id+"""</FolderID>
        <Status>%s</Status>
    </Result>"""
end_xml = """</Tims>"""

query_xml = ''
i=0

#filepath = os.path.join(report_dir, 'report.xml')
filepath = args.results_xml
data = open(filepath).read().replace('\n','')
data = data.split('</Testcase>')

for i in range(0,len(data)-1):
    tc_name = re.search(r'<TestcaseName>.*</TestcaseName>',data[i]).group()
    tc_name = re.search(">(.*)<", tc_name).group(1)
    tc_status = re.search(r'<Status>.*</Status>', data[i]).group()
    tc_status = re.search(">(.*)<", tc_status).group(1)
    print (tc_name, tc_status)

    if tc_status=="Failed":
        print "Encountered failure"
        if i!=0:
            query_xml = query_xml + filler_xml % ((tc_name), 'failed')
            print "query xml :",query_xml
        else:
            query_xml = start_xml + filler_xml % ((tc_name), 'failed')
            print "query xml :",query_xml
    else:
        print "Encountered passed"
        if i!=0:
            query_xml = query_xml + filler_xml % ((tc_name), 'passed')
            print "query xml :",query_xml
        else:
            query_xml = start_xml + filler_xml % ((tc_name), 'passed')
            print "query xml :",query_xml
            i=i+1

query_xml = query_xml + end_xml
print "********************************Final query xml******************" ,query_xml

#Declare connection handles and variables
obj = Tims3xIO(USERNAME='shuchugh')
url = "http://tims.cisco.com"
path = "xml/Tps212p/entity.svc"

def parse_tims_result(xml_out):
    tree =  ET.fromstring(xml_out)
    for child in tree:
        if child.text.endswith('f'):
            return child.text

try:
    msg = obj.send(BASE=url, PATH=path, METHOD='POST', XML=query_xml, PROXY=sys_proxy)
    print "msg sent:" +msg


except:
    print "There was a problem getting to TIMS", sys.exc_info()[0]
    raise