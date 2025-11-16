"""
Test Gemini API connection and corpus access

Uses your actual API key and project.

Author: Brady Flink / Claude
Date: November 2025
Version: 1.0
"""
import google.generativeai as genai
import os
import sys

# Credentials from environment variables (NEVER hardcode API keys!)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_PROJECT = os.getenv("GEMINI_PROJECT", "projects/624887625185")

if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY environment variable not set")
    print("Please set it with: set GEMINI_API_KEY=your_api_key")
    sys.exit(1)


def test_basic_connection():
    """Test basic Gemini API connection"""
    print("\n🔍 Testing Gemini API connection...")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    try:
        # Test simple generation
        response = genai.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Explain how AI works in a few words"
        )
        print(f"✅ Basic API works!")
        print(f"   Response: {response.text[:150]}...")
        return True
    except Exception as e:
        print(f"❌ API failed: {e}")
        return False


def test_corpus_access():
    """Test corpus access and list available corpora"""
    print("\n🔍 Testing corpus access...")
    
    try:
        # List available corpora
        corpora = list(genai.list_corpora())
        print(f"✅ Found {len(corpora)} corpus(es):")
        
        for corpus in corpora:
            print(f"\n   📚 Corpus: {corpus.name}")
            print(f"      Display Name: {corpus.display_name if hasattr(corpus, 'display_name') else 'N/A'}")
            print(f"      Create Time: {corpus.create_time if hasattr(corpus, 'create_time') else 'N/A'}")
        
        if len(corpora) == 0:
            print("\n⚠️  No corpora found yet.")
            print("\n📋 TO CREATE YOUR FIRST CORPUS:")
            print("   1. Run: python scripts/setup_gemini_corpus.py")
            print("   2. This generates 834 HTML files on your Desktop")
            print("   3. Visit https://aistudio.google.com")
            print("   4. Click 'Create Corpus' or 'New Corpus'")
            print("   5. Name: eagle_sign_master_knowledge")
            print("   6. Description: 95 years of Eagle Sign project history")
            print("   7. Drag the entire Desktop/Gemini_Eagle_Knowledge_Base/ folder")
            print("   8. Wait 10-15 minutes for indexing")
            print("   9. Come back and run this test again!")
        
        return len(corpora) > 0
        
    except Exception as e:
        print(f"❌ Corpus access failed: {e}")
        print("\n💡 This might be a permissions issue. Verify:")
        print("   - API key is correct")
        print("   - Project ID is correct (624887625185)")
        print("   - API key has File Search enabled")
        return False


def test_file_search():
    """Test File Search RAG if corpus exists"""
    print("\n🔍 Testing File Search RAG...")
    
    try:
        corpora = list(genai.list_corpora())
        if not corpora:
            print("❌ No corpus available for testing")
            print("   Create a corpus first (see instructions above)")
            return False
        
        corpus = corpora[0]
        print(f"   Using corpus: {corpus.name}")
        
        # Test query
        print("   Running test query: 'What are Cat Scale standard part specifications?'")
        
        response = genai.generate_content(
            model="gemini-2.0-flash-exp",
            contents="What are Cat Scale standard part specifications and pricing?",
            tools=[genai.Tool(file_search={"corpus_id": corpus.name})]
        )
        
        print(f"\n✅ RAG query successful!")
        print(f"   Response preview: {response.text[:300]}...")
        
        # Check for citations (File Search should include them)
        if hasattr(response, 'grounding_metadata'):
            print(f"\n📚 Citations found: {len(response.grounding_metadata.grounding_chunks) if hasattr(response.grounding_metadata, 'grounding_chunks') else 0}")
        
        return True
        
    except Exception as e:
        print(f"❌ File Search failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Verify corpus has documents uploaded")
        print("   - Check corpus indexing is complete (wait 10-15 min after upload)")
        print("   - Try simpler query if complex queries fail")
        return False


def test_model_listing():
    """List available Gemini models"""
    print("\n🔍 Listing available Gemini models...")
    
    try:
        models = genai.list_models()
        print(f"✅ Available models:")
        
        for model in models:
            if 'flash' in model.name or 'pro' in model.name:
                print(f"   - {model.name}")
        
        return True
    except Exception as e:
        print(f"❌ Model listing failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("GEMINI API TEST SUITE")
    print("SignX Platform - SignX Platform Integration")
    print("=" * 70)
    print(f"\nProject: SignX")
    print(f"Project ID: {GEMINI_PROJECT}")
    print(f"API Key: {GEMINI_API_KEY[:20]}...{GEMINI_API_KEY[-10:]}")
    print("=" * 70)
    
    # Run tests
    results = {}
    
    results["1. Basic Connection"] = test_basic_connection()
    results["2. Model Listing"] = test_model_listing()
    results["3. Corpus Access"] = test_corpus_access()
    results["4. File Search RAG"] = test_file_search()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:30} {status}")
    
    all_passed = all(results.values())
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Gemini API is fully operational")
        print("✅ Ready to build instant quotes")
    else:
        print(f"⚠️  {passed_count}/{total_count} TESTS PASSED")
        if not results.get("3. Corpus Access"):
            print("\n📋 NEXT STEP: Generate and upload your corpus")
            print("   Run: python scripts/setup_gemini_corpus.py")
        if not results.get("1. Basic Connection"):
            print("\n❌ CRITICAL: API connection failed")
            print("   Check your API key and internet connection")
    
    print("=" * 70 + "\n")
    
    input("Press Enter to exit...")
    sys.exit(0 if all_passed else 1)

