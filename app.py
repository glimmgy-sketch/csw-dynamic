from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# နမူနာ Test User များနဲ့ ဗီဒီယိုအစပျိုးများ
videos = [
    {
        'id': 1,
        'url': 'https://www.w3schools.com/html/mov_bbb.mp4',
        'caption': 'Dynamic Studio မှာ ကိုယ်ကာယလေ့ကျင့်ခန်း လုပ်ကြမယ်လေ 🔥💪',
        'location': 'Dynamic Studio (မကွေးမြို့)',
        'username': 'Min Naung Myint Soe',
        'reactions': {'Min Naung Myint Soe': '❤️', 'thuza': '🔥'},
        'comment_count': 1
    },
    {
        'id': 2,
        'url': 'https://www.w3schools.com/html/movie.mp4',
        'caption': 'Zumba Class အမိုက်စား စနေပါပြီ 💃✨',
        'location': 'Dynamic Studio (မကွေးမြို့)',
        'username': 'thuza',
        'reactions': {'Min Naung Myint Soe': '👍'},
        'comment_count': 0
    }
]

comments_db = {
    1: [
        {'username': 'thuza', 'text': 'လာခဲ့မယ်လေ ညီလေးရေ 👍', 'image_url': None}
    ]
} 

user_bios = {
    'Min Naung Myint Soe': 'Dynamic Studio ရဲ့ တည်ထောင်သူ / ပုံမှန်ကစားသူတစ်ဦးပါ ✨',
    'thuza': 'Dynamic Studio ရဲ့ ပုံမှန်ကစားသူတစ်ဦးပါ ✨',
    'ko_hla': 'Fitness & Health lover 💪'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_video():
    data = request.json
    new_video = {
        'id': len(videos) + 1,
        'url': data.get('url'),
        'caption': data.get('caption', ''),
        'location': data.get('location', 'Dynamic Studio (မကွေးမြို့)'),
        'username': data.get('username', 'Min Naung Myint Soe'),
        'reactions': {},
        'comment_count': 0
    }
    videos.insert(0, new_video)
    return jsonify({'success': True, 'video': new_video})

@app.route('/api/feed')
def get_feed():
    current_user = request.args.get('username', 'Min Naung Myint Soe')
    feed_data = []
    
    for v in videos:
        v_copy = v.copy()
        reactions = v.get('reactions', {})
        v_copy['user_reaction'] = reactions.get(current_user, None)
        
        breakdown = {}
        for emoji in reactions.values():
            breakdown[emoji] = breakdown.get(emoji, 0) + 1
            
        v_copy['reactions_breakdown'] = breakdown
        v_copy['total_reactions'] = len(reactions)
        v_copy['comment_count'] = len(comments_db.get(v['id'], []))
        
        feed_data.append(v_copy)
        
    return jsonify(feed_data)

@app.route('/api/my-videos')
def get_my_videos():
    username = request.args.get('username', 'Min Naung Myint Soe')
    user_videos = []
    
    for v in videos:
        if v.get('username') == username:
            v_copy = v.copy()
            v_copy['total_reactions'] = len(v.get('reactions', {}))
            user_videos.append(v_copy)
            
    return jsonify(user_videos)

@app.route('/api/search')
def search_videos():
    query = request.args.get('q', '').lower()
    matched_videos = []
    
    for v in videos:
        caption = v.get('caption', '').lower()
        username = v.get('username', '').lower()
        location = v.get('location', '').lower()
        
        if query in caption or query in username or query in location:
            v_copy = v.copy()
            v_copy['total_reactions'] = len(v.get('reactions', {}))
            matched_videos.append(v_copy)
            
    return jsonify(matched_videos)

@app.route('/api/bio', methods=['GET', 'POST'])
def handle_bio():
    username = request.args.get('username') or (request.json.get('username', 'Min Naung Myint Soe') if request.json else 'Min Naung Myint Soe')
    if request.method == 'POST':
        data = request.json
        bio_text = data.get('bio', '')
        user_bios[username] = bio_text
        return jsonify({'success': True, 'bio': bio_text})
    
    default_bio = "Dynamic Studio (မကွေးမြို့) 🔥 ဖျော်ဖြေရေးနှင့် ကြံ့ခိုင်ရေး ဗီဒီယိုများ"
    return jsonify({'bio': user_bios.get(username, default_bio)})

@app.route('/api/react', methods=['POST'])
def react_video():
    data = request.json
    video_id = data.get('video_id')
    emoji = data.get('emoji', '❤️')
    username = data.get('username', 'Min Naung Myint Soe')
    
    for v in videos:
        if v['id'] == video_id:
            if 'reactions' not in v:
                v['reactions'] = {}
            if v['reactions'].get(username) == emoji:
                del v['reactions'][username]
            else:
                v['reactions'][username] = emoji
            break
            
    return jsonify({'success': True})

@app.route('/api/comments/<int:video_id>')
def get_comments(video_id):
    return jsonify(comments_db.get(video_id, []))

@app.route('/api/comment/<int:video_id>', methods=['POST'])
def post_comment(video_id):
    data = request.json
    if video_id not in comments_db:
        comments_db[video_id] = []
        
    comment = {
        'username': data.get('username', 'Min Naung Myint Soe'),
        'text': data.get('text', ''),
        'image_url': data.get('image_url', None)
    }
    comments_db[video_id].append(comment)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
