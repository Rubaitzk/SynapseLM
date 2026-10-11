import re

def update():
    with open("frontend/src/pages/ConversationView.tsx", "r", encoding="utf-8") as f:
        content = f.read()

    select_html = """          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={aiConfig.ai_model}
              onChange={e => setAiConfig({...aiConfig, ai_model: e.target.value})}
            >
              {aiConfig.ai_provider === 'gemini' && (
                <>
                  <option value="gemini-3.5-flash">gemini-3.5-flash</option>
                  <option value="gemini-3.8-flash">gemini-3.8-flash</option>
                  <option value="gemini-3.8-flash-lite">gemini-3.8-flash-lite</option>
                  <option value="gemini-3.8-flash-tts">gemini-3.8-flash-tts</option>
                </>
              )}
              {aiConfig.ai_provider === 'openai' && (
                <>
                  <option value="gpt-4o">gpt-4o</option>
                  <option value="gpt-4-turbo">gpt-4-turbo</option>
                  <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                </>
              )}
              {aiConfig.ai_provider === 'mock' && (
                <option value="mock">mock</option>
              )}
            </select>
          </div>"""

    old_input = """          <Input 
            label="Model"
            value={aiConfig.ai_model}
            onChange={e => setAiConfig({...aiConfig, ai_model: e.target.value})}
          />"""

    content = content.replace(old_input, select_html)
    
    with open("frontend/src/pages/ConversationView.tsx", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update()
