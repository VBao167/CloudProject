from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

app = Flask(__name__)

# --- Kết nối tới MongoDB Cloud (Atlas) ---
client = MongoClient("mongodb+srv://BaoDBUser:BaoBaoBao@cluster0.yy17x7j.mongodb.net/?appName=Cluster0")
db = client["cloud_homework"]
collection = db["users"]

# --- Hàm chuyển ObjectId sang chuỗi (trả về bản copy, an toàn với list hoặc dict) ---
def to_json(data):
    """
    Nếu data là list -> trả list mới với _id chuyển thành str (nếu có).
    Nếu data là dict -> trả dict mới với _id chuyển thành str (nếu có).
    Nếu không -> trả nguyên giá trị.
    """
    if isinstance(data, list):
        out = []
        for item in data:
            new_item = dict(item)
            if "_id" in new_item:
                new_item["_id"] = str(new_item["_id"])
            out.append(new_item)
        return out
    if isinstance(data, dict):
        new_item = dict(data)
        if "_id" in new_item:
            new_item["_id"] = str(new_item["_id"])
        return new_item
    return data

# --- API: Thêm người dùng ---
@app.route("/add", methods=["POST"])
def add_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Dữ liệu không hợp lệ!"}), 400

    # Required: name, age
    name = data.get("name")
    age = data.get("age")
    country_side = data.get("countrySide", "")

    if not name:
        return jsonify({"status": "error", "message": "Vui lòng nhập tên!"}), 400
    if age is None or str(age).strip() == "":
        return jsonify({"status": "error", "message": "Vui lòng nhập tuổi!"}), 400

    # Kiểm tra age có thể chuyển thành int không
    try:
        age_int = int(age)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Tuổi phải là một số nguyên hợp lệ!"}), 400

    user_data = {
        "name": name,
        "age": age_int,
        "countrySide": country_side or ""
    }

    try:
        result = collection.insert_one(user_data)
    except Exception as e:
        return jsonify({"status": "error", "message": "Lỗi khi thêm vào cơ sở dữ liệu", "error": str(e)}), 500

    response = {
        "status": "success",
        "message": "Thêm thành công!",
        "inserted_id": str(result.inserted_id)
    }

    # Nếu countrySide chưa nhập -> thêm alert để frontend hiển thị cảnh báo
    if not user_data["countrySide"]:
        response["alert"] = "Chưa nhập quê quán"

    return jsonify(response), 201

# --- API: Xem toàn bộ người dùng ---
@app.route("/list", methods=["GET"])
def list_users():
    try:
        users = list(collection.find())
        users_json = to_json(users)
        return jsonify({"status": "success", "data": users_json}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Lỗi khi truy vấn cơ sở dữ liệu", "error": str(e)}), 500

# --- API: Xem chi tiết theo tên ---
@app.route("/find/<name>", methods=["GET"])
def find_user(name):
    try:
        user = collection.find_one({"name": name})
        if not user:
            return jsonify({"status": "error", "message": "Không tìm thấy người dùng"}), 404
        return jsonify({"status": "success", "data": to_json(user)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Lỗi khi truy vấn", "error": str(e)}), 500

# --- API: Cập nhật thông tin người dùng ---
@app.route("/update/<id>", methods=["PUT"])
def update_user(id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Dữ liệu không hợp lệ!"}), 400

    update_data = {}
    # Cho phép update name, age, countrySide
    if "name" in data:
        if data["name"]:
            update_data["name"] = data["name"]
        else:
            # Nếu muốn cho phép clear name -> có thể xử lý khác, ở đây ta không cho name rỗng
            return jsonify({"status": "error", "message": "Tên không được để trống"}), 400
    if "age" in data:
        try:
            update_data["age"] = int(data["age"])
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Tuổi phải là số nguyên hợp lệ"}), 400
    if "countrySide" in data:
        # Allow empty string to clear field if client wants
        update_data["countrySide"] = data.get("countrySide", "")

    if not update_data:
        return jsonify({"status": "error", "message": "Không có dữ liệu để cập nhật"}), 400

    # Convert id -> ObjectId, xử lý InvalidId
    try:
        obj_id = ObjectId(id)
    except InvalidId:
        return jsonify({"status": "error", "message": "ID không hợp lệ"}), 400

    try:
        result = collection.update_one({"_id": obj_id}, {"$set": update_data})
        if result.matched_count == 0:
            return jsonify({"status": "error", "message": "Không tìm thấy người dùng với ID này"}), 404
        return jsonify({"status": "success", "message": "Cập nhật thành công!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Lỗi khi cập nhật cơ sở dữ liệu", "error": str(e)}), 500

# --- API: Xóa người dùng theo ID ---
@app.route("/delete/<id>", methods=["DELETE"])
def delete_user(id):
    try:
        obj_id = ObjectId(id)
    except InvalidId:
        return jsonify({"status": "error", "message": "ID không hợp lệ"}), 400

    try:
        result = collection.delete_one({"_id": obj_id})
        if result.deleted_count == 0:
            return jsonify({"status": "error", "message": "Không tìm thấy người dùng để xóa"}), 404
        return jsonify({"status": "success", "message": "Xóa thành công!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Lỗi khi xóa dữ liệu", "error": str(e)}), 500

# --- API kiểm tra kết nối ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Connected successfully !"})

@app.route("/web")
def web_ui():
    return render_template("index.html")

if __name__ == "__main__":
    # debug=True chỉ nên dùng khi phát triển
    app.run(host="0.0.0.0", port=5000, debug=True)
