import re

filepath = r'D:\Hackathons\SynapseLM\frontend\src\pages\ConversationView.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add sidebarOpen state
content = content.replace(
    'const [showConfig, setShowConfig] = useState(false);',
    'const [showConfig, setShowConfig] = useState(false);\n  const [sidebarOpen, setSidebarOpen] = useState(true);'
)

# Update right sidebar div
content = content.replace(
    '<div className="hidden lg:flex w-72 flex-col bg-white border-l border-gray-200 shrink-0">',
    '{sidebarOpen && (\n        <div className="hidden lg:flex w-72 flex-col bg-white border-l border-gray-200 shrink-0">'
)

content = content.replace(
    '            </div>\n          </div>\n        </div>\n      </div>',
    '            </div>\n          </div>\n        </div>\n      )}\n      </div>'
)

# Add toggle button in header
header_btn_target = '<Button variant="secondary" size="sm" onClick={() => setShowConfig(true)}>\n              <Cpu size={16} className="mr-2" />\n              AI: {conversation.ai_provider}\n            </Button>'
header_btn_replacement = '''<div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => setShowConfig(true)}>
                <Cpu size={16} className="mr-2" />
                AI: {conversation.ai_provider}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(!sidebarOpen)} className="hidden lg:flex text-gray-500">
                <Users size={16} className="mr-1" />
                {sidebarOpen ? 'Hide' : 'Show'}
              </Button>
            </div>'''
content = content.replace(header_btn_target, header_btn_replacement)

# Import fix if needed
if 'import { Trash2' in content and 'PanelRight' not in content:
    content = content.replace('Trash2, Send, Users', 'Trash2, Send, Users, PanelRight')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
