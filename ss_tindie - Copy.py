'''
Need to do SKU to correct model name lookup
            set shipping service
            set package size
            set confirmation
            set customs info


            https://www.shipstation.com/docs/api/products/get-product/
'''

import tindie
from ShipStation import *
import pycountry

# setup
tindieOrders = tindie.TindieOrdersAPI('Username', 'API_Key')
api_key = 'API_Key' # shipstation api key
api_secret = 'API_Secret' # shipstation api secret
ss = ShipStation(key=api_key, secret=api_secret)
ss.debug = True

# define functions
def to_shipstation_date(d):
    # 2017-07-19T13:13:04.282464
    # 12/8/2011 21:56 PM
        
    year = d.strftime('%Y') #returns 4 digit year
    month = d.strftime('%m') #returns 2 digit month
    day = d.strftime('%d') #returns day
    hour24 = d.strftime('%H') #returns 24 hour
    minute = d.strftime('%M') #returns minutes
    PM = d.strftime('%p') #returns AM/PM
    
    return "%s/%s/%s %s:%s %s" % (month, day, year, hour24, minute, PM)

# We can also filter in only unshipped orders by setting shipped to False
# Setting it to true would filter in only shipped orders!
#json_data = tindieOrders.get_orders_json(False)
order_data = tindieOrders.get_orders(False)

for i in order_data:
    print(i.order_number)
    print(i.address_dict['country'])
    country = pycountry.countries.get(name=i.address_dict['country']).alpha_2
    print(country)

    ss_Order = ShipStationOrder(order_number = i.order_number) # set the SS order number to the Tindie order number
    ss_Order.set_status('awaiting_shipment') # set the order status: awaiting_payment, awaiting_shipment, shipped, on_hold, cancelled
    ss_Order.set_confirmation('none')
    ss_Order.set_customer_details(username='', email=i.recipient_email) # username is optional. Want the include the email address though.
    
    shipping_address = ShipStationAddress( # Tindie shipping and billing address should be the same, but build in capability.
        name=i.address_dict['recipient_name'].title(), 
        company=i.address_dict['company'],
        street1=i.address_dict['street'], street2='', street3='', 
        city=i.address_dict['city'].title(), state=i.address_dict['state'].title(), 
        postal_code=i.address_dict['postcode'], country=country, # converty country name to 2 character code
        phone=i.recipient_phone, residential='')
    billing_address = ShipStationAddress(
        name=i.address_dict['recipient_name'].title(), 
        company=i.address_dict['company'],
        street1=i.address_dict['street'], street2='', street3='', 
        city=i.address_dict['city'].title(), state=i.address_dict['state'].title(), 
        postal_code=i.address_dict['postcode'], country=country, # converty country name to 2 character code
        phone=i.recipient_phone, residential='')
    
    ss_Order.set_shipping_address(shipping_address) # set the shipping address
    ss_Order.set_billing_address(billing_address) # set the billing address
    ss_Order.set_order_date(i.date) # conversion isn't needed          set the order date (after converting Tindie date to ShipStation date: 2017-07-19T13:13:04.282464 to 12/8/2011 21:56 PM) to_shipstation_date(i.date)
    ss_Order.set_payment_date(i.date)
    ss_Order.shipping_amount = i.shipping_cost
    ss_Order.amount_paid = i.subtotal
    ss_Order.customer_notes = i.address_dict['instructions']
    ss_Order.internal_notes = i.message
    ss_Order.payment_method = 'Tindie'
    
    ss_Weight = ShipStationWeight(units='ounces', value='0')
    ss_Container = ShipStationContainer(units='inches', length='6', width='9', height='1')
    ss_Order.set_dimensions(ss_Container)
    #ss_Container.set_weight(ss_Weight) # weight seems to be broken - disabled in ShipStation.py

    for q in i.products:
        ss_Item = ShipStationItem(
            key='', 
            sku=q.sku, 
            name=q.name, 
            image_url='', 
            quantity=q.qty, 
            unit_price=q.price, 
            warehouse_location='', 
            options='') #q.options) # options doesn't work right - need to fix
        #ss_Item.set_weight('1') # weight seems to be broken - disabled in ShipStation.py
        ss_Order.add_item(ss_Item)

    ss.add_order(ss_Order)
    ss.submit_orders()

'''
last_order = tindie.get_last_order()
result_list = [int(v) for k,v in last_order.products[0].model]
print(result_list)
print(last_order.products[0].price) '''