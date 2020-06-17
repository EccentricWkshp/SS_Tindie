'''
SS_Tindie by EccentricWorkshop (ecc.ws or github.com/EccentricWkshp)
based on the work of https://github.com/natecox/pyshipstation and https://github.com/NuclearManD/TindieAPI
Initial on 06/10/2020

Automatically gets Tindie storeId from ShipStation if config.SS_Tindie_StoreID = '' or uses config value if set.
Checks for new, unshipped order from Tindie.
Gets all shipped and awaiting_shipment orders from ShipStation (all pages) for Tindie_StoreId.
Removes all orders already sent to ShipStation.
Submits new orders from Tindie.

Tindie API doesn't provide the model number for products with multiple options unless the main model number is not blank.

Need to do SKU to correct model name lookup
        only submit new orders not already in SS -> done
        set shipping service
        set package size
        set confirmation -> done
        set customs info
        build advancedOptions -> done
        automatically get Tindie storeId from ShipStation -> done

ShipStation API Docs: https://www.shipstation.com/docs/api/products/get-product/
'''

import pycountry_convert as pcc
from ShipStation import *
import tindie
import config

# setup
tindieOrders = tindie.TindieOrdersAPI(config.T_username, config.T_api_key)
ss = ShipStation(key=config.SS_api_key, secret=config.SS_api_secret)

ss.debug = True # show ShipStation debug info

# get stores from ShipStation
SS_Tindie_Store_Auto = ss.fetch_stores().json()
#print(json.dumps(SS_Tindie_Store_Auto, indent=4)) # print JSON formatted SS_Tindie_Store_Auto for debugging
for i in SS_Tindie_Store_Auto: # step through each item in SS_Tindie_Store_Auto
    #print(i['storeId'], i['storeName']) # print out the combinations to check them
    if i['storeName'] == 'Tindie':
        Tindie_StoreId = i['storeId']
    else:
        continue # no Tindie store found in i['storeName'], check the next one

if not config.SS_Tindie_StoreID: # check to see if config.SS_Tindie_StoreID is empty
    config.SS_Tindie_StoreID = Tindie_StoreId # is empty so set it to the value automatically found
elif config.SS_Tindie_StoreID: # check to see if config.SS_Tindie_StoreID is not empty
    Tindie_StoreId = config.SS_Tindie_StoreID # has a value so set Tindie_StoreId to the config value
else: # any other case
    print("error!") # let us know there's a problem

def populate_order(data):
    i = data
 
    print("Processing order number", i.order_number) # bit of debugging to show the order number

    #print(i.country)
    order_country = pcc.country_name_to_country_alpha2(i.country, cn_name_format="default") # convert country name to 2 character code
    #print(pcc.country_name_to_country_alpha2(i.country, cn_name_format="default"))

    ss_Order = ShipStationOrder(order_number = i.order_number) # set the SS order number to the Tindie order number
    ss_Order.set_status('awaiting_shipment') # set the order status: awaiting_payment, awaiting_shipment, shipped, on_hold, cancelled
    ss_Order.set_confirmation('none') # set the 
    ss_Order.set_customer_details(username='', email=i.recipient_email) # username is optional. Want the include the email address though.
    
    advancedoptions = ShipStationAdvancedOptions( # build out the advancedOptions
        billToAccount='', billToCountryCode='', billToMyOtherAccount='', billToParty='', billToPostalCode='',
        containsAlcohol='False',
        customField1='', customField2='', customField3='',
        mergedIds='', mergedOrSplit='False',
        nonMachinable='False', parentID='', saturdayDelivery='False',
        source='Tindie', storeID=Tindie_StoreId, warehouseId=''
    )
    ss_Order.set_advanced_options(advancedoptions) # set the advancedOptions
    
    shipping_address = ShipStationAddress( # Tindie shipping and billing address should be the same through Tindie, but build in the capability.
        name=i.recipient_name.title(), 
        company=i.company,
        street1=i.street, street2='', street3='', 
        city=i.city.title(), state=i.state.title(), 
        postal_code=i.postcode, country=order_country,
        phone=i.recipient_phone, residential=''
    )
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

    ss_Order.set_create_date(i.date) # set the order creation to the order date from Tindie
    ss_Order.set_order_date(i.date) # set the order date to the order date from Tindie
    ss_Order.set_payment_date(i.date) # set the payment date to the order date from Tindie. This is ok because Tindie orders have to be paid immediately.
    ss_Order.shipping_amount = i.shipping_cost # set the shipping amount to the shipping cost from Tindie
    ss_Order.amount_paid = i.subtotal # set the order amount paid to the subtotal from Tindie. Tindie doesn't collect tax yet so this is all that is needed here.
    ss_Order.customer_notes = i.instructions  #i.address_dict['instructions'] save to move back to address_dict later
    ss_Order.internal_notes = i.message # set the order internal notes to the order message from Tindie.
    ss_Order.payment_method = 'Tindie' # set the payment method to Tindie
    
    ss_Container = ShipStationContainer(units='inches', length='6', width='9', height='1')
    ss_Order.set_dimensions(ss_Container)

    ss_Container.set_weight(ShipStationWeight(units='ounces', value='0')) # weight seems to be broken - disabled in ShipStation.py

    for q in i.products: # build out each item based on the information from Tindie
        print("model:", q.model)
        print("sku:", q.sku)
        ss_Item = ShipStationItem(
            key='', # no key is used, this is to identify the OrderItem in the originating system
            sku=q.sku, # SKU from Tindie
            name=q.name, # item name from Tindie
            image_url='', # image URL if wanted, Tindie doesn't offer this.
            quantity=q.qty, # quantity of the item from Tindie
            unit_price=q.unit_price, # unit price from Tindie, .price will give the price_total from Tindie which is the per item subtotal
            warehouse_location='', # Tindie doesn't provide this but it can be set based on ShipStation settings
            options='') #q.options) # options doesn't work right - need to fix
        ss_Item.set_weight(ShipStationWeight(units='ounces', value='3')) # weight seems to be broken
        ss_Order.add_item(ss_Item) # add the ss_Item to the current order

    ss.add_order(ss_Order) # add the ss_Order to the current order
    print("Finished", i.order_number) # bit of debugging
# end of populate_order

#json_data = tindieOrders.get_orders_json(False)
order_data = tindieOrders.get_orders(False) # get the orders from Tindie. True = all orders, False = only unshipped

# get orders from ShipStation
response_shipped = ss.fetch_orders(parameters={'store_id': Tindie_StoreId , 'order_status': 'shipped'}) # get exising 'shipped' orders from ShipStation
response_await = ss.fetch_orders(parameters={'store_id': Tindie_StoreId, 'order_status': 'awaiting_shipment'}) # get existing 'awaiting shipment' orders from ShipStation

response_shipped = response_shipped.json() # format the shipped response as JSON
response_await = response_await.json() # format the awaiting response as JSON

ss_Existing_Shipped = response_shipped['orders']
ss_Existing_Await = response_await['orders']

for page in range(2, response_shipped['pages']+1): # step through the pages from current page to pages+1
    response_shipped = ss.fetch_orders(parameters={'store_id': Tindie_StoreId, 'order_status': 'shipped', 'page': page}).json() # get the next page of responses
    ss_Existing_Shipped.extend(response_shipped['orders']) # extend the dictionary with the current page of responses

for page in range(2, response_await['pages']+1):
    response_await = ss.fetch_orders(parameters={'store_id': Tindie_StoreId, 'order_status': 'awaiting_shipment', 'page': page}).json() # get the next page of responses
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

#SSset.remove('198870') # only here for testing to get into the all new orders case
#Tset.remove('195777')

if Tset.intersection(SSset): # check to see if any elements of Tset intersect SSset
    print(len(Tset.intersection(SSset)), "duplicate orders found.")
    for i in Tset.intersection(SSset):
        print("Removed", i) # let us know this order has already been submitted to ShipStation
        Tset.remove(i) # remove the duplicate order
    
    print(len(Tset), "new orders found.")
    
    for i in Tset: # step through all items in Tset
        print("New order", i) # tell us if we have a new order

        for x in range(len(order_data)): # step through each item in order_data
            if str(order_data[x].order_number) == i: # check to see if the order_number from Tindie is the same as the new order
                #print(order_data[x].order_number, order_data[x].recipient_name) # just a bit of checking on things
                populate_order(order_data[x]) # process the new order into a ShipStation order object
else: # all orders are new
    print(len(Tset), "orders are new.") # let us know
    for i in Tset: # step through all items in Tset
        print("Submitted", i) # tell us if we have a new order

        for x in range(len(order_data)): # step through each item in order_data
            if str(order_data[x].order_number) == i: # this should always be true, but just in case check to see if the order_number from Tindie is the same as the new order
                #print(order_data[x].order_number, order_data[x].recipient_name) # just a bit of checking on things
                populate_order(order_data[x]) # process the new order into a ShipStation order object

ss.submit_orders() # disable for testing so the order doesn't get submitted