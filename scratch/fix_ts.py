import os
import re

app_layout_path = r'D:\Hackathons\SynapseLM\frontend\src\components\layout\AppLayout.tsx'
with open(app_layout_path, 'r') as f:
    content = f.read()
content = content.replace('MessageSquare, Users, Settings, LogOut, Menu', 'MessageSquare, Users, LogOut, Menu')
with open(app_layout_path, 'w') as f:
    f.write(content)

conv_view_path = r'D:\Hackathons\SynapseLM\frontend\src\pages\ConversationView.tsx'
with open(conv_view_path, 'r') as f:
    content = f.read()
content = content.replace("import { useParams, Link, useNavigate } from 'react-router-dom';", "import { useParams, useNavigate } from 'react-router-dom';")
content = content.replace('Settings, Trash2, Send, X, Users, AlertCircle, Cpu', 'Trash2, Send, Users, AlertCircle, Cpu, MessageSquare')
with open(conv_view_path, 'w') as f:
    f.write(content)

home_path = r'D:\Hackathons\SynapseLM\frontend\src\pages\Home.tsx'
with open(home_path, 'r') as f:
    content = f.read()
content = content.replace("import React, { useState, useEffect } from 'react';", "import { useState, useEffect } from 'react';")
content = content.replace('const navigate = useNavigate();', '')
content = content.replace("import { Link, useNavigate } from 'react-router-dom';", "import { Link } from 'react-router-dom';")
content = content.replace('map(p => p.catch(e => ({ data: [] })))', 'map(p => p.catch(() => ({ data: [] })))')
with open(home_path, 'w') as f:
    f.write(content)

print('Fixed TS errors')
