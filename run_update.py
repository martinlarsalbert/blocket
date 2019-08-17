"""
This modeule is an example of the update_blocket can be used to retrieve some data from blocket.s
"""


import update_blocket as ub
from collections import OrderedDict

car_paths = OrderedDict()
car_paths['kangoo'] = r'https://www.blocket.se/hela_sverige?q=&cg=1020&w=3&st=s&ps=&pe=&mys=&mye=&ms=&me=&cxpf=&cxpt=&fu=&gb=&ccco=1&ca=15&is=1&l=0&md=th&cp=&cb=30&cbl1=4'
car_paths['berlingo'] = r'https://www.blocket.se/hela_sverige?q=&cg=1020&w=3&st=s&ps=&pe=&mys=&mye=&ms=&me=&cxpf=&cxpt=&fu=&gb=&ca=15&is=1&l=0&md=th&cp=&cb=7&cbl1=1'
car_paths['caddy'] = r'https://www.blocket.se/hela_sverige?q=&cg=1020&w=3&st=s&ps=&pe=&mys=&mye=&ms=&me=&cxpf=&cxpt=&fu=&gb=&ccco=1&ca=15&is=1&l=0&md=th&cp=&cb=40&cbl1=2'

cars_path = 'cars.csv'

df_cars = ub.load_from_blocket(car_paths=car_paths, max_cars=None)
df_cars = ub.combine_new_and_old(file_path=cars_path,df_cars=df_cars)
ub.save(file_path=cars_path,df_cars=df_cars)