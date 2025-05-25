# Examples Directory

Quick-start examples for getting up and running with webcam-detection package.

## 🚀 Quick Start (RECOMMENDED)

**For Production Use:**

1. **Start the HTTP service:**
   ```bash
   python webcam_http_service.py
   ```

2. **Use HTTP guard clause in your code:**
   ```python
   import requests
   
   def should_process_audio():
       try:
           response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
           return response.json().get("human_present", False)
       except:
           return True  # Fail safe
   ```

## 📁 What's Here

- **`package_usage_examples.py`** - Production-ready integration patterns
  - ✅ HTTP service startup (recommended)
  - ✅ Speaker verification guard clauses  
  - ✅ Client wrapper classes
  - ✅ Direct API usage (alternative)
  - ✅ Docker deployment examples

## 🆚 Examples vs Docs

| **Purpose** | **Use This** |
|-------------|--------------|
| 🚀 **Get started quickly** | `examples/` - Simple, working code |
| 📖 **Learn comprehensive patterns** | `docs/` - Detailed architecture & advanced patterns |
| 🎯 **Speaker verification integration** | `examples/package_usage_examples.py` |
| 🏗️ **Custom service architecture** | `docs/service_patterns.py` |
| 📚 **Complete API reference** | `docs/PACKAGE_USAGE.md` |

## 🏃 Run Examples

```bash
# Run all examples
python examples/package_usage_examples.py

# Or specific examples
python -c "from examples.package_usage_examples import example_speaker_verification_production; example_speaker_verification_production()"
```

## 💡 Next Steps

1. **Quick prototype**: Start with examples here
2. **Production deployment**: Reference `docs/production_service_patterns.py`
3. **Advanced patterns**: See `docs/service_patterns.py`
4. **API reference**: Check `docs/PACKAGE_USAGE.md` 