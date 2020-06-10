'''
06/10/2020

Tindie API doesn't seem to provide the model number despite that being listed in the documentation.

Need to do SKU to correct model name lookup
            set shipping service
            set package size
            set confirmation -> done
            set customs info


            https://www.shipstation.com/docs/api/products/get-product/
'''

import config
import tindie
from ShipStation import *
import pycountry_convert as pcc

# setup
tindieOrders = tindie.TindieOrdersAPI(config.T_username, config.T_api_key)

ss = ShipStation(key=config.SS_api_key, secret=config.SS_api_secret)
ss.debug = True

# define functions
def to_shipstation_date(d):
    # was needed but shipstation appears to now accecpt the standard date format
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
# Setting it to true would filter in only shipped orders
#json_data = tindieOrders.get_orders_json(False)
order_data = tindieOrders.get_orders(False)

for i in order_data:
    print("Order number:", i.order_number)

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

    ''' Preserve this for later
    billing_address = ShipStationAddress(
        name=i.address_dict['recipient_name'].title(), 
        company=i.address_dict['company'],
        street1=i.address_dict['street'], street2='', street3='', 
        city=i.address_dict['city'].title(), state=i.address_dict['state'].title(), 
        postal_code=i.address_dict['postcode'], country=order_country,
        phone=i.recipient_phone, residential='')
    '''
    
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

ss.submit_orders() # disable for testing so the order doesn't get submitted

''' testing of the get_last_order feature
last_order = tindie.get_last_order()
result_list = [int(v) for k,v in last_order.products[0].model]
print(result_list)
print(last_order.products[0].price)
'''
