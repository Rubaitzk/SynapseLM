import re

def update():
    with open("frontend/src/pages/ConversationView.tsx", "r", encoding="utf-8") as f:
        content = f.read()

    # Replace handleSend error handling
    old_catch = """      } catch (err: any) {
        addToast(err.response?.data?.detail || "Failed to send message", "error");
        setContent(payload); // restore content
      }"""
    
    new_catch = """      } catch (err: any) {
        if (err.response?.data?.error_code === 'provider_configuration_missing') {
          addToast("Provider configuration missing. Please configure AI settings.", "error");
          setShowConfig(true);
        } else if (err.response?.data?.error_code === 'invalid_provider_model_combo') {
          addToast("Invalid provider/model combination selected.", "error");
          setShowConfig(true);
        } else if (err.response?.data?.error_code === 'unsupported_provider') {
          addToast("Selected provider is not supported.", "error");
          setShowConfig(true);
        } else {
          addToast(err.response?.data?.detail || "Failed to send message", "error");
        }
        setContent(payload); // restore content
      }"""
      
    content = content.replace(old_catch, new_catch)
    
    with open("frontend/src/pages/ConversationView.tsx", "w", encoding="utf-8") as f:
        f.write(content)

    with open("frontend/src/pages/NewConversation.tsx", "r", encoding="utf-8") as f:
        content_nc = f.read()
        
    old_catch_nc = """    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to start conversation.', 'error');
      setIsSubmitting(false);
    }"""
    
    new_catch_nc = """    } catch (err: any) {
      if (err.response?.data?.error_code === 'provider_configuration_missing') {
        addToast("Backend provider configuration missing. Check environment variables.", "error");
      } else {
        addToast(err.response?.data?.detail || 'Failed to start conversation.', 'error');
      }
      setIsSubmitting(false);
    }"""
    
    content_nc = content_nc.replace(old_catch_nc, new_catch_nc)
    
    with open("frontend/src/pages/NewConversation.tsx", "w", encoding="utf-8") as f:
        f.write(content_nc)
        
if __name__ == "__main__":
    update()
