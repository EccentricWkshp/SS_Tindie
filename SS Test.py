'''
06/13/2020 SS_Tindie

Checks for new, unshipped order from Tindie
Gets all shipped and awaiting_shipment orders from ShipStation (all pages) for config.SS_Tindie_StoreID
Removes all orders already sent to ShipStation
Submits new orders from Tindie

Tindie API doesn't seem to provide the model number despite that being listed in the documentation.

Need to do SKU to correct model name lookup
        only submit new orders not already in SS -> done
        set shipping service
        set package size
        set confirmation -> done
        set customs info

ShipStation API Docs: https://www.shipstation.com/docs/api/products/get-product/
'''

import config
import tindie
from ShipStation import *
import pycountry_convert as pcc

# setup
tindieOrders = tindie.TindieOrdersAPI(config.T_username, config.T_api_key)
ss = ShipStation(key=config.SS_api_key, secret=config.SS_api_secret)

ss.debug = False # show ShipStation debug info

def populate_order(data):
    i = data
    if True: # lazily fix the indent issue for now
    #for i in data: #was order_data
        print("Order number", i.order_number, "is new, processing.") # bit of debugging to show the order number

        #print(i.country)
        order_country = pcc.country_name_to_country_alpha2(i.country, cn_name_format="default") # convert country name to 2 character code
        #print(pcc.country_name_to_country_alpha2(i.country, cn_name_format="default"))

        ss_Order = ShipStationOrder(order_number = i.order_number) # set the SS order number to the Tindie order number
        ss_Order.set_status('awaiting_shipment') # set the order status: awaiting_payment, awaiting_shipment, shipped, on_hold, cancelled
        ss_Order.set_confirmation('none')
        ss_Order.set_customer_details(username='', email=i.recipient_email) # username is optional. Want the include the email address though.
        #ss_Order.advanced_options['storeId': 68270] # need to implement this function
        
        shipping_address = ShipStationAddress( # Tindie shipping and billing address should be the same through Tindie, but build in the capability.
            name=i.recipient_name.title(), 
            company=i.company,
            street1=i.street, street2='', street3='', 
            city=i.city.title(), state=i.state.title(), 
            postal_code=i.postcode, country=order_country,
            phone=i.recipient_phone, residential='')
        
        billing_address = shipping_address # set the two addresses to be the same since Tindie only provides one address.

        '''#Preserve this for later
        billing_address = ShipStationAddress(
            name=i.address_dict['recipient_name'].title(), 
            company=i.address_dict['company'],
            street1=i.address_dict['street'], street2='', street3='', 
            city=i.address_dict['city'].title(), state=i.address_dict['state'].title(), 
            postal_code=i.address_dict['postcode'], country=order_country,
            phone=i.recipient_phone, residential='')
        '''#
        ss_Order.set_shipping_address(shipping_address) # set the shipping address
        ss_Order.set_billing_address(billing_address) # set the billing address
        ss_Order.set_order_date(i.date) # set the order date to the order date from Tindie
        ss_Order.set_payment_date(i.date) # set the payment date to the order date from Tindie. This is ok because Tindie orders have to be paid immediately.
        ss_Order.shipping_amount = i.shipping_cost # set the shipping amount to the shipping cost from Tindie
        ss_Order.amount_paid = i.subtotal # set the order amount paid to the subtotal from Tindie. Tindie doesn't collect tax yet so this is all that is needed here.
        ss_Order.customer_notes = i.instructions  #i.address_dict['instructions'] save to move back to address_dict later
        ss_Order.internal_notes = i.message # set the order internal notes to the order message from Tindie.
        ss_Order.payment_method = 'Tindie' # set the payment method to Tindie, not sure if this is working
        
        ss_Weight = ShipStationWeight(units='ounces', value='0')
        ss_Container = ShipStationContainer(units='inches', length='6', width='9', height='1')
        ss_Order.set_dimensions(ss_Container)
        #ss_Container.set_weight(ss_Weight) # weight seems to be broken - disabled in ShipStation.py

        for q in i.products: # build out each item based on the information from Tindie
            ss_Item = ShipStationItem(
                key='', # no key is used, this is to identify the OrderItem in the originating system
                sku=q.sku, # SKU from Tindie
                name=q.name, # item name from Tindie
                image_url='', # image URL if wanted, Tindie doesn't offer this.
                quantity=q.qty, # quantity of the item from Tindie
                unit_price=q.unit_price, # unit price from Tindie, .price will give the price_total from Tindie which is the per item subtotal
                warehouse_location='', # Tindie doesn't provide this but it can be set based on ShipStation settings
                options='') #q.options) # options doesn't work right - need to fix
            #ss_Item.set_weight('1') # weight seems to be broken - disabled in ShipStation.py
            ss_Order.add_item(ss_Item) # add the ss_Item to the current order

        ss.add_order(ss_Order) # add the ss_Order to the current order
        print("Order number", i.order_number, "has been processed.") # bit of debugging

#json_data = tindieOrders.get_orders_json(False)
order_data = tindieOrders.get_orders(False) # get the orders from Tindie. True = all orders, False = only unshipped

# get orders from ShipStation
response_shipped = ss.fetch_orders(parameters={'store_id': config.SS_Tindie_StoreID, 'order_status': 'shipped'}) # get exising 'shipped' orders from ShipStation
response_await = ss.fetch_orders(parameters={'store_id': config.SS_Tindie_StoreID, 'order_status': 'awaiting_shipment'}) # get existing 'awaiting shipment' orders from ShipStation

response_shipped = response_shipped.json() # format the shipped response as JSON
response_await = response_await.json() # format the awaiting response as JSON

ss_Existing_Shipped = response_shipped['orders']
ss_Existing_Await = response_await['orders']

for page in range(2, response_shipped['pages']+1): # step through the pages from current page to pages+1
    response_shipped = ss.fetch_orders(parameters={'store_id': config.SS_Tindie_StoreID, 'order_status': 'shipped', 'page': page}).json() # get the next page of responses
    ss_Existing_Shipped.extend(response_shipped['orders']) # extend the dictionary with the current page of responses

for page in range(2, response_await['pages']+1):
    response_await = ss.fetch_orders(parameters={'store_id': config.SS_Tindie_StoreID, 'order_status': 'awaiting_shipment', 'page': page}).json() # get the next page of responses
    ss_Existing_Await.extend(response_await['orders']) # extend the dictionary with the current page of responses

''' # print JSON out to file for saving and debugging
with open('await_all.json', 'w') as f:
    json.dump(ss_Existing_Await, f, indent=4)
with open('shipped_all.json', 'w') as f:
    json.dump(ss_Existing_Shipped, f, indent=4)
'''
Tset = set() # define Tset as an empty set
SSset = set() # define SSset as an empty set

for order in order_data: # step through each new Tindie order and add it to the set Tset
    Tset.add(str(order.order_number)) # add new orders pulled from Tindie to Tset
for i, order in enumerate(ss_Existing_Await): # step through each order in ss_Existing_Awaiting and add it to the set SSset
    SSset.add(str(order['orderNumber']))
for i, order in enumerate(ss_Existing_Shipped): # step through each order in ss_Existing_Shipped and add it to the set SSset
    SSset.add(str(order['orderNumber']))

#Tset.remove('198870') # only here for testing to get into the all new orders case

if Tset.intersection(SSset): # check to see if any elements of Tset intersect SSset
    print("Duplicate orders found.")
    for i in Tset.intersection(SSset):
        print("Order", i, "already submitted, removing.") # let us know this order has already been submitted to ShipStation
        Tset.remove(i) # remove the duplicate order
    for i in Tset: # step through all items in Tset
        print("Order", i, "is new, submitting.") # tell us if we have a new order

        for x in range(len(order_data)): # step through each item in order_data
            if str(order_data[x].order_number) == i: # check to see if the order_number from Tindie is the same as the new order
                #print(order_data[x].order_number, order_data[x].recipient_name) # just a bit of checking on things
                populate_order(order_data[x]) # process the new order into a ShipStation order object
else: # all orders are new
    print("All orders are new.") # let us know
    for i in Tset: # step through all items in Tset
        print("Order", i, "is new, submitting.") # tell us if we have a new order

        for x in range(len(order_data)): # step through each item in order_data
            if str(order_data[x].order_number) == i: # this should always be true, but just in case check to see if the order_number from Tindie is the same as the new order
                #print(order_data[x].order_number, order_data[x].recipient_name) # just a bit of checking on things
                populate_order(order_data[x]) # process the new order into a ShipStation order object

#ss.submit_orders() # disable for testing so the order doesn't get submitted