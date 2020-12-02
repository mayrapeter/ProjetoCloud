import requests
import sys
from datetime import datetime
import json

for arg in sys.argv:
    print(arg)

def get_dns(name):
    f = open(name + ".txt", "r")
    if f.mode == 'r':
        dns = f.read()
    return dns

dns = get_dns("dns_loadbalancer")


url = 'http://' + dns + ':8080/tasks'



def get():
    response = requests.get(url + '/get')
    print("A resposta da requisição foi:")
    print(response.text)

def add(payload):
    response = requests.post(url + '/add', data=json.dumps(payload))
    print("A resposta da requisição foi:")
    print(response.text)

def delete():
    response = requests.delete(url + '/delete')
    print("A resposta da requisição foi:")
    print(response.text)

# para fazer um request, rodar com:
# get: python client.py get
# post: python client.py add titulo descricao
# delete: python client.py delete
if __name__ ==  '__main__':
    if sys.argv[1] == 'get':
        print("Procurando a rota /get...")
        get()
    elif sys.argv[1] == 'add':
        if len(sys.argv) >= 4:
            print("Procurando a rota /add...")
            title = sys.argv[2]
            description = sys.argv[3]
            pub_date = datetime.now().isoformat()
            payload = {'title':title, 'pub_date':pub_date, 'description': description}
            add(payload)
        else: 
            print("Argumentos insuficientes. Passe primeiramente o nome do arquivo, depois a função a ser chamada (get ou add). Se a função for get, não são necessários outros argumentos. Se for add, o 2º argumento é o título e o 3º é a descrição")
    elif sys.argv[1] == 'delete':
        print("Procurando a rota /delete...")
        delete()