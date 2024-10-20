# Importação
from flask import Flask, request, jsonify, send_from_directory
import os
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = "minha_chave_123"

# Caminho correto para o SQLite (relativo à pasta do projeto)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'

login_manager = LoginManager()
db = SQLAlchemy(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
CORS(app)

SWAGGER_URL = '/swagger' 
API_URL = '/swagger.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,      
    API_URL,              
    config={               
        'app_name': "E-commerce API"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Rota para servir o arquivo swagger.yaml
@app.route('/swagger.yaml')
def swagger_yaml():
    return send_from_directory(os.getcwd(), 'swagger.yaml')

#Criando banco de dados de usuarios
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    userName = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=True)
    cart = db.relationship('CartItem', backref='user', lazy=True)

#banco de dados para o carrinho 
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_list = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

#Autenticacao
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Login do usuario
@app.route('/login', methods=["POST"] )
def login():
    data = request.json

    user = User.query.filter_by(userName=data.get("username")).first()
    
    if user and data.get("password") == user.password:
            login_user(user)
            return jsonify({"message": "Logged in successfully"})
    return jsonify({"message": "Unauthorized. Invalid credentials"}), 401

#Criando o logout
@app.route('/logout', methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successfully"})

# Criando tabela para produtos
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

#adicionar um produto no banco de dados
@app.route('/api/products/add', methods=["POST"])
@login_required
def add_product():
    data = request.json
    if 'name' in data and 'price' in data:
        product = Product(name=data["name"], price=data["price"], description=data.get("description", ""))
        db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Product added successfully"})
    return jsonify({"message": "Invalid product data"}), 400

#deletar produto do banco de dados
@app.route('/api/products/delete/<int:product_id>', methods=["DELETE"])
@login_required
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit ()
        return jsonify({"message": "Product deleted successfully"})
    return jsonify({"message": "Product not found"}), 404

#detalhes do produto
@app.route('/api/products/<int:product_id>', methods=["GET"])
def get_product_details(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify ({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description
        })
    return jsonify ({"message": "Product not found"}), 404

#Atualizar produtos no banco de dados
@app.route('/api/products/update/<int:product_id>', methods=["PUT"])
@login_required
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"message": "Product not found"}), 404

    #alterar o valor do produto e atualizar
    data = request.json
    if 'name' in data:
        product.name = data['name']

    if 'price' in data:
        product.price = data['price']

    if 'description' in data:
        product.description = data['description']

    db.session.commit()
    return jsonify({"message": "Product updated successfully"})

#Pegar todos os registro do banco de dados
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    product_list = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
        }
        product_list.append(product_data)
    return jsonify(product_list)

#Adicionar produto no cart
@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    #obtem o usuario atual
    user = User.query.get(int(current_user.id))
    #obtem o produto a partir do ID
    product = Product.query.get(product_id)

    if user and product:
        cart_item = CartItem(user_id=user.id, product_list= product.id)
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"message": "Item added to the cart successfully"})
    return jsonify({"message": "Failed to add item to the cart"}), 400


#remover produto do cart
@app.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_list=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Item removed from the cart successfully"})
    return jsonify({"message": "Failed to remove item from the cart"}), 400

#Listagem dos itens que tem no cart
@app.route('/api/cart', methods=['GET'])
@login_required
def view_cart():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    cart_content = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_list )
        cart_content.append({
            "id": cart_item.id,
            "user_id":cart_item.user_id,
            "product_id":cart_item.product_list,
            "product_name": product.name,
            "product_price": product.price
        })
        print(cart_item)
    return jsonify(cart_content), 400

@app.route('/api/cart/checkout', methods=["POST"])
@login_required
def checkout():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    for cart_item in cart_items:
        db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'message': 'Checkout successful. Cart has been cleared.'})

if __name__ == "__main__":
    app.run(debug=True)
