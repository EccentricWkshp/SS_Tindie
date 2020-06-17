from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

import xml.dom.minidom as minidom
import pycountry
import traceback

chrome_options = Options()  
chrome_options.add_argument("--headless")  

drivers = {}

def set_order_tracking_id(driver, username, password, order_id, tracking_id):
    order_id = unicode(order_id)
    tracking_id = unicode(tracking_id)

    driver.get("https://www.tindie.com/orders/unshipped/")

    # log in to tindie if needed
    try:
        username_input = driver.find_element_by_name("EccentricWkshp")
        password_input = driver.find_element_by_name("aE8N8$GGjG")

        username_input.send_keys(username)
        password_input.send_keys(password)
        username_input.submit()

    except:
        pass

    # get unshipped orders
    orders_table = driver.find_element_by_id("orders-table")
    order_rows = orders_table.find_elements_by_tag_name("tr")

    # remove header
    order_rows.pop(0)

    for row in order_rows:
        # get the order id
        row_order_id = row.find_element_by_tag_name("strong").text
        print(row_order_id)

        # input the tracking code
        if row_order_id == order_id:
            tracking_code_input = row.find_element_by_name("tracking_code")
            tracking_code_input.send_keys(tracking_id)
            row.find_element_by_name("shipped").click()

import urlfetch
import json

def xml(data):
    xml_string = ""
    if isinstance(data, dict):
        for k, v in data.iteritems():
            xml_string += "<%s>%s</%s>" % (k, xml(v), k)
    elif isinstance(data, list):
        for v in data:
            xml_string += xml(v)
    else:
        xml_string += str(data).strip()

    return xml_string

            
 
def pretty_xml(data):
    return minidom.parseString("<Orders pages=\"1\">" + xml(data).strip() + "</Orders>").toprettyxml()



def cdata(txt):
    if isinstance(txt, (int, long)):
        return "<![CDATA[" + unicode(txt) + "]]>"
    else:
        return "<![CDATA[" + txt.encode("utf-8") + "]]>"

def to_shipstation_date(d):
    # 2017-07-19T13:13:04.282464
    # 12/8/2011 21:56 PM

    year = d[0:4]
    month = d[5:7]
    day = d[8:10]
    hour24 = d[11:13]
    minute = d[14:16]
    
    return "%s/%s/%s %s:%s" % (month, day, year, hour24, minute) 


def to_shipstation_status(o):
    if bool(o['shipped']):
        return 'shipped'
    elif bool(o['refunded']):
        return 'cancelled'
    else:
        return 'paid'
            

def to_shipstation_last_modified(o):
    if bool(o['shipped']):
        return to_shipstation_date(o['date_shipped'])
    else:
        return to_shipstation_date(o['date'])



def to_shipstation_country(c):
    if "south korea" in c.lower():
        return u'kr'
    elif "russia" in c.lower():
        return u'ru'
    else:
        return cdata(pycountry.countries.lookup(c).alpha_2)



def to_shipstation_customer(o):
    return {
        'CustomerCode': cdata(o['email']),
        'BillTo': {
            'Name': cdata(o['shipping_name'])
        },
        'ShipTo': {
            'Name': cdata(o['shipping_name']),
            'Company': cdata(o['company_title']),
            'Address1': cdata(o['shipping_street']),
            'City': cdata(o['shipping_city']),
            'State': cdata(o['shipping_state']),
            'PostalCode': cdata(o['shipping_postcode']),
            'Country': to_shipstation_country(o['shipping_country']),
            'Phone': cdata(o['phone'])
        },
    }



def to_shipstation_option(option):
    (name, value) = option.split(": ")
    return {
        'Name': cdata(name),
        'Value': cdata(value)
    }



def to_shipstation_options(options):
    try:
        return [{'Option': to_shipstation_option(o)} for o in options[1:-1].split("; ")]
    except:
        traceback.print_exc()
        print(str(options))
        return []


def to_shipstation_item(i):
    return {
        'SKU': cdata(i['sku']),
        'Name': cdata(i['product']),
        'Quantity': i['quantity'],
        'UnitPrice': i['price_unit'],
        'Options': to_shipstation_options(i['options'])
    }



def to_shipstation_items(items):
    return [{'Item': to_shipstation_item(i)} for i in items]



def to_shipstation_order(o):
    return {
        'OrderID': cdata(o['number']),
        'OrderNumber': cdata(o['number']),
        'OrderDate': to_shipstation_date(o['date']),
        'OrderStatus': to_shipstation_status(o),
        'LastModified': to_shipstation_last_modified(o),
        'ShippingMethod': cdata(o['shipping_service']),
        'OrderTotal': str(o['total_subtotal']),
        'TaxAmount': "0.00",
        'ShippingAmount': str(o['total_shipping']),
        'CustomerNotes': cdata(o['shipping_instructions']),
        'Customer': to_shipstation_customer(o),
        'Items': to_shipstation_items(o['items']),
    }



def to_shipstation_fmt(tindie_orders):
    return [{'Order': to_shipstation_order(o)} for o in tindie_orders['orders']]



from flask import Flask
from flask import request, abort
app = Flask(__name__)


@app.route('/tindie', methods=['GET'])
def tindie_get():
    p = request.args
    
    username = p['SS-UserName']
    (api_key, password) = p['SS-Password'].split()
    url = "https://www.tindie.com/api/v1/order/?format=json&shipped=false&username=%s&api_key=%s" % (username, api_key)

    result = urlfetch.fetch(url)
    
    if result.status_code == 200:
        orders = json.loads(result.content)
        return pretty_xml(to_shipstation_fmt(orders))
    else:
        abort(result.status_code)


@app.route('/tindie', methods=['POST'])
def tindie_update():
    p = request.args 

    username = p['SS-UserName']
    (api_key, password) = p['SS-Password'].split()
    order_id = p['order_number']
    tracking_id = p['tracking_number']
    token = username + password

    if p['action'] == 'shipnotify':
        # share drivers between requests ONLY if the username and password match
        if token not in drivers:
            drivers[token] = webdriver.Chrome(chrome_options=chrome_options)
        
        # get the appropriate web driver
        driver = drivers[token]

        # drive the web!
        set_order_tracking_id(driver, username, password, order_id, tracking_id)

    return ""
