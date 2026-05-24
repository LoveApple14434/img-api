# img_api.py
import os
import random
import time
from flask import Flask, send_file, jsonify, request
from flask_cors import CORS
import glob
import hashlib
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 配置 - 两个图片目录
IMAGE_DIR_ZIPPED = "source/img-zipped"   # 原有压缩图片目录
IMAGE_DIR_RAW = "source/img"             # 新增原始图片目录
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
CACHE_FILE_ZIPPED = "image_cache_zipped.json"
CACHE_FILE_RAW = "image_cache_raw.json"

class ImageManager:
    def __init__(self, image_dir, cache_file):
        self.image_dir = image_dir
        self.cache_file = cache_file
        self.images = []
        self.last_update = 0
        self.cache_duration = 300  # 缓存5分钟

    def scan_directory(self):
        """扫描目录获取所有图片"""
        print(f"开始扫描目录: {self.image_dir}")
        images = []

        try:
            for root, dirs, files in os.walk(self.image_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        images.append({
                            'path': file_path,
                            'filename': file,
                            'ext': ext,
                            'relative': os.path.relpath(file_path, self.image_dir)
                        })

            self.images = images
            self.last_update = time.time()
            self.save_cache()
            print(f"找到 {len(images)} 张图片")
            return images

        except Exception as e:
            print(f"扫描目录时出错: {e}")
            return []

    def load_cache(self):
        """从缓存文件加载"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.images = data.get('images', [])
                    self.last_update = data.get('last_update', 0)
                    print(f"从缓存加载了 {len(self.images)} 张图片 ({self.image_dir})")
                    return True
        except Exception as e:
            print(f"加载缓存时出错: {e}")
        return False

    def save_cache(self):
        """保存到缓存文件"""
        try:
            data = {
                'images': self.images,
                'last_update': self.last_update,
                'total': len(self.images),
                'scan_time': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"保存缓存时出错: {e}")

    def get_images(self):
        """获取图片列表，使用缓存"""
        current_time = time.time()

        if (not self.images or
            (current_time - self.last_update) > self.cache_duration):
            if not self.load_cache():
                self.scan_directory()

        return self.images

    def get_random_image(self, category=None, seed=None):
        """获取随机图片"""
        images = self.get_images()
        if not images:
            return None

        if seed:
            random.seed(seed)

        if category:
            filtered = [img for img in images if category in img['filename'].lower()]
            if filtered:
                return random.choice(filtered)

        return random.choice(images)

# 初始化两个管理器
image_manager_zipped = ImageManager(IMAGE_DIR_ZIPPED, CACHE_FILE_ZIPPED)
image_manager_raw = ImageManager(IMAGE_DIR_RAW, CACHE_FILE_RAW)

# -------------------- 原有 API（使用 source/img-zipped）--------------------
@app.route('/random-image', methods=['GET'])
def get_random_image_zipped():
    """获取随机图片（压缩目录）"""
    category = request.args.get('category')
    seed = request.args.get('seed')
    width = request.args.get('width')
    height = request.args.get('height')

    img_info = image_manager_zipped.get_random_image(category, seed)

    if not img_info:
        return jsonify({
            "error": "No images found",
            "path": IMAGE_DIR_ZIPPED
        }), 404

    try:
        response = send_file(
            img_info['path'],
            mimetype=f'image/{img_info["ext"][1:]}',
            as_attachment=False,
            conditional=True
        )
        response.headers['X-Image-Name'] = img_info['filename']
        response.headers['X-Image-Path'] = img_info['relative']
        response.headers['X-Total-Images'] = len(image_manager_zipped.images)
        return response

    except Exception as e:
        return jsonify({
            "error": str(e),
            "path": img_info['path']
        }), 500

# -------------------- 新增 API（使用 source/img）--------------------
@app.route('/random-image-raw', methods=['GET'])
def get_random_image_raw():
    """获取随机图片（原始目录）"""
    category = request.args.get('category')
    seed = request.args.get('seed')
    width = request.args.get('width')
    height = request.args.get('height')

    img_info = image_manager_raw.get_random_image(category, seed)

    if not img_info:
        return jsonify({
            "error": "No images found",
            "path": IMAGE_DIR_RAW
        }), 404

    try:
        response = send_file(
            img_info['path'],
            mimetype=f'image/{img_info["ext"][1:]}',
            as_attachment=False,
            conditional=True
        )
        response.headers['X-Image-Name'] = img_info['filename']
        response.headers['X-Image-Path'] = img_info['relative']
        response.headers['X-Total-Images'] = len(image_manager_raw.images)
        return response

    except Exception as e:
        return jsonify({
            "error": str(e),
            "path": img_info['path']
        }), 500

# -------------------- 刷新缓存接口 --------------------
@app.route('/refresh', methods=['POST', 'GET'])
def refresh_cache_zipped():
    """刷新原有压缩目录的缓存"""
    old_count = len(image_manager_zipped.images)
    image_manager_zipped.scan_directory()
    new_count = len(image_manager_zipped.images)

    return jsonify({
        "status": "success",
        "message": "Zipped cache refreshed",
        "data": {
            "old_count": old_count,
            "new_count": new_count,
            "added": new_count - old_count if new_count > old_count else 0,
            "removed": old_count - new_count if old_count > new_count else 0,
            "timestamp": datetime.now().isoformat()
        }
    })

@app.route('/refresh-raw', methods=['POST', 'GET'])
def refresh_cache_raw():
    """刷新新增原始目录的缓存"""
    old_count = len(image_manager_raw.images)
    image_manager_raw.scan_directory()
    new_count = len(image_manager_raw.images)

    return jsonify({
        "status": "success",
        "message": "Raw cache refreshed",
        "data": {
            "old_count": old_count,
            "new_count": new_count,
            "added": new_count - old_count if new_count > old_count else 0,
            "removed": old_count - new_count if old_count > new_count else 0,
            "timestamp": datetime.now().isoformat()
        }
    })

# -------------------- 主页 --------------------
@app.route('/')
def index():
    """API主页"""
    total_zipped = len(image_manager_zipped.get_images())
    total_raw = len(image_manager_raw.get_images())

    return f"""
    <html>
        <head>
            <title>随机图片API - /img-api</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    max-width: 1000px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #FFD1DC 0%, #FFC0CB 100%);
                    color: #333;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                h1 {{ text-align: center; margin-bottom: 40px; }}
                .stats {{
                    background: rgba(255, 255, 255, 0.2);
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    text-align: center;
                }}
                .endpoint {{
                    background: rgba(255, 255, 255, 0.15);
                    padding: 20px;
                    margin: 15px 0;
                    border-radius: 10px;
                    border-left: 4px solid #4CAF50;
                }}
                code {{
                    background: rgba(255, 255, 255, 0.9);
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }}
                .method {{
                    display: inline-block;
                    background: #4CAF50;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                a {{
                    color: #90CAF9;
                    text-decoration: none;
                }}
                a:hover {{ text-decoration: underline; }}
                .example {{ 
                    background: rgba(255, 255, 255, 0.6); 
                    padding: 10px; 
                    border-radius: 5px;
                    margin: 10px 0;
                    overflow-x: auto;
                }}
                .back-home {{
                    position: absolute;
                    top: 20px;
                    left: 20px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 16px;
                    background: rgba(255, 255, 255, 0.2);
                    backdrop-filter: blur(5px);
                    border-radius: 10px;
                    text-decoration: none;
                    color: #333;
                    font-weight: bold;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    transition: all 0.3s ease;
                }}
                .back-home:hover {{
                    background: rgba(255, 255, 255, 0.3);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
                    transform: translateY(-2px);
                    text-decoration: none;
                    color: #000;
                }}
                .back-home::before {{
                    content: "←";
                    font-size: 18px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="https://loveapple.icu" class="back-home">返回主页</a>
                <h1>🖼️ 随机图片 API</h1>
                <div class="stats">
                    <h2>📊 统计信息</h2>
                    <p>图片总数: <strong>{total_raw}</strong> 张</p>
                    <p>本页面由AI生成 This page is generated by AI</p>
                </div>

                <div class="endpoint">
                    <div class="method">GET</div>
                    <code>/img-api/random-image</code>
                    <p>获取随机图片（来自压缩目录 <code>source/img-zipped</code>）</p>
                    <div class="example">
                        示例：<br><br>
                        <a href="https://loveapple.icu/img-api/random-image" target="_blank">
                        <code>https://loveapple.icu/img-api/random-image</code>
                        </a><br><br>
                        <a href="https://loveapple.icu/img-api/random-image?seed=123" target="_blank">
                        <code>https://loveapple.icu/img-api/random-image?seed=123</code>
                        </a>
                    </div>
                </div>

                <div class="endpoint">
                    <div class="method">GET</div>
                    <code>/img-api/random-image-raw</code>
                    <p>获取随机图片（来自原始目录 <code>source/img</code>）</p>
                    <div class="example">
                        示例：<br><br>
                        <a href="https://loveapple.icu/img-api/random-image-raw" target="_blank">
                        <code>https://loveapple.icu/img-api/random-image-raw</code>
                        </a><br><br>
                        <a href="https://loveapple.icu/img-api/random-image-raw?seed=456" target="_blank">
                        <code>https://loveapple.icu/img-api/random-image-raw?seed=456</code>
                        </a>
                    </div>
                </div>

                <div class="endpoint">
                    <div class="method">POST/GET</div>
                    <code>/img-api/refresh</code>
                    <p>刷新压缩目录的图片缓存</p>
                </div>

                <div class="endpoint">
                    <div class="method">POST/GET</div>
                    <code>/img-api/refresh-raw</code>
                    <p>刷新原始目录的图片缓存</p>
                </div>
            </div>

            <div id="demo-status" style="text-align: center; margin-top: 20px;"></div>
            <script>
                fetch('/img-api/random-image')
                    .then(response => {{
                        const imgName = response.headers.get('X-Image-Name');
                        if (imgName) {{
                            document.getElementById('demo-status').innerHTML = 
                                `🎉 API（压缩目录）运行正常！最近一张图片：<code>${{imgName}}</code>`;
                        }}
                    }})
                    .catch(error => {{
                        document.getElementById('demo-status').innerHTML = 
                            '⚠️ API连接测试失败，请检查服务是否运行';
                    }});
            </script>
        </body>
    </html>
    """

def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0 or unit == 'GB':
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} {unit}"

if __name__ == '__main__':
    print("🚀 启动随机图片API服务...")
    print(f"📁 压缩图片目录: {IMAGE_DIR_ZIPPED}")
    print(f"📁 原始图片目录: {IMAGE_DIR_RAW}")
    print(f"🌐 API路径前缀: /img-api")

    if not os.path.exists(IMAGE_DIR_ZIPPED):
        print(f"⚠️ 警告：压缩图片目录不存在: {IMAGE_DIR_ZIPPED}")
    if not os.path.exists(IMAGE_DIR_RAW):
        print(f"⚠️ 警告：原始图片目录不存在: {IMAGE_DIR_RAW}")

    # 加载两个缓存
    print("🔄 正在加载压缩目录缓存...")
    image_manager_zipped.load_cache()
    if not image_manager_zipped.images:
        print("📂 压缩目录缓存为空，开始扫描...")
        image_manager_zipped.scan_directory()

    print("🔄 正在加载原始目录缓存...")
    image_manager_raw.load_cache()
    if not image_manager_raw.images:
        print("📂 原始目录缓存为空，开始扫描...")
        image_manager_raw.scan_directory()

    print(f"✅ 压缩目录加载完成，共 {len(image_manager_zipped.images)} 张图片")
    print(f"✅ 原始目录加载完成，共 {len(image_manager_raw.images)} 张图片")
    print(f"🔗 本地测试地址: http://127.0.0.1:5001")
    print(f"🌐 生产访问地址: https://your-domain.com/img-api")
    print(f"🖼️  随机图片示例: https://your-domain.com/img-api/random-image")
    print(f"🖼️  原始图片示例: https://your-domain.com/img-api/random-image-raw")

    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)