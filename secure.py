# email_setup.py - Run this script to set up email configuration
import os

def setup_email_config():
    """Interactive script to set up email configuration"""
    print("🚀 Skill Buddy Email Configuration Setup")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = '.env'
    env_content = []
    
    if os.path.exists(env_file):
        print("✅ Found existing .env file")
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    else:
        print("📝 Creating new .env file")
    
    # Helper function to update or add env variable
    def update_env_var(key, value):
        updated = False
        for i, line in enumerate(env_content):
            if line.startswith(f"{key}="):
                env_content[i] = f"{key}={value}\n"
                updated = True
                break
        if not updated:
            env_content.append(f"{key}={value}\n")
    
    print("\n📧 Email Provider Selection:")
    print("1. Gmail (recommended)")
    print("2. Outlook/Hotmail")
    print("3. Yahoo Mail")
    print("4. Custom SMTP")
    
    choice = input("\nSelect your email provider (1-4): ").strip()
    
    if choice == "1":
        # Gmail setup
        print("\n📧 Gmail Configuration")
        print("⚠️  Important: You must use an App Password, not your regular password!")
        print("\nTo create an App Password:")
        print("1. Go to https://myaccount.google.com/security")
        print("2. Enable 2-Step Verification")
        print("3. Go to App passwords")
        print("4. Generate password for 'Mail'")
        print("5. Use the 16-character password below")
        
        email = input("\nEnter your Gmail address: ").strip()
        app_password = input("Enter your Gmail App Password (16 characters): ").strip()
        
        update_env_var("SMTP_SERVER", "smtp.gmail.com")
        update_env_var("SMTP_PORT", "587")
        update_env_var("SMTP_USERNAME", email)
        update_env_var("SMTP_PASSWORD", app_password)
        update_env_var("SMTP_USE_TLS", "True")
        update_env_var("FROM_EMAIL", email)
        
    elif choice == "3":
        # Yahoo setup
        print("\n📧 Yahoo Mail Configuration")
        email = input("Enter your Yahoo email address: ").strip()
        password = input("Enter your password: ").strip()
        
        update_env_var("SMTP_SERVER", "smtp.mail.yahoo.com")
        update_env_var("SMTP_PORT", "587")
        update_env_var("SMTP_USERNAME", email)
        update_env_var("SMTP_PASSWORD", password)
        update_env_var("SMTP_USE_TLS", "True")
        update_env_var("FROM_EMAIL", email)
        
    elif choice == "4":
        # Custom SMTP setup
        print("\n📧 Custom SMTP Configuration")
        smtp_server = input("Enter SMTP server (e.g., mail.yourhost.com): ").strip()
        smtp_port = input("Enter SMTP port (587 for TLS, 465 for SSL): ").strip()
        use_tls = input("Use TLS? (y/n): ").strip().lower() == 'y'
        email = input("Enter your email address: ").strip()
        password = input("Enter your email password: ").strip()
        
        update_env_var("SMTP_SERVER", smtp_server)
        update_env_var("SMTP_PORT", smtp_port)
        update_env_var("SMTP_USERNAME", email)
        update_env_var("SMTP_PASSWORD", password)
        update_env_var("SMTP_USE_TLS", "True" if use_tls else "False")
        update_env_var("FROM_EMAIL", email)
    
    else:
        print("❌ Invalid choice")
        return
    
    # Additional settings
    from_name = input("\nEnter sender name (default: Skill Buddy): ").strip()
    if not from_name:
        from_name = "Skill Buddy"
    update_env_var("FROM_NAME", from_name)
    
    frontend_url = input("Enter frontend URL (default: http://localhost:3000): ").strip()
    if not frontend_url:
        frontend_url = "http://localhost:3000"
    update_env_var("FRONTEND_URL", frontend_url)
    
    # Write to .env file
    with open(env_file, 'w') as f:
        f.writelines(env_content)
    
    print(f"\n✅ Email configuration saved to {env_file}")
    print("\n🔄 Next steps:")
    print("1. Restart your Flask application")
    print("2. Test your configuration using: curl -X GET http://localhost:5000/api/debug/email-config")
    print("3. Send a test email using: curl -X POST http://localhost:5000/api/debug/send-test-email -H 'Content-Type: application/json' -d '{\"email\":\"your-test@email.com\"}'")
    
    # Test configuration
    test_now = input("\n🧪 Test configuration now? (y/n): ").strip().lower()
    if test_now == 'y':
        test_email_config()

def test_email_config():
    """Test the email configuration"""
    print("\n🧪 Testing email configuration...")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import email service
        from services.email_service import EmailService
        email_service = EmailService()
        
        print(f"Email service enabled: {email_service.enabled}")
        
        if not email_service.enabled:
            print("❌ Email service is disabled. Check your environment variables.")
            return
        
        # Test connection
        print("Testing SMTP connection...")
        connection_ok = email_service.test_connection()
        
        if connection_ok:
            print("✅ SMTP connection successful!")
            
            # Ask for test email
            test_email = input("Enter email address to send test email (or press Enter to skip): ").strip()
            if test_email:
                print(f"Sending test email to {test_email}...")
                
                subject = "🎉 Skill Buddy Email Test"
                html_content = """
                <h2>Email Configuration Test Successful!</h2>
                <p>Congratulations! Your Skill Buddy email configuration is working correctly.</p>
                <p><strong>✅ SMTP connection: OK</strong></p>
                <p><strong>✅ Email sending: OK</strong></p>
                """
                text_content = "Email Configuration Test Successful!\nYour Skill Buddy email configuration is working correctly."
                
                success = email_service.send_email([test_email], subject, html_content, text_content)
                
                if success:
                    print("✅ Test email sent successfully!")
                    print("Check your inbox (and spam folder) for the test email.")
                else:
                    print("❌ Test email failed to send.")
            
        else:
            print("❌ SMTP connection failed. Check your credentials and settings.")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    setup_email_config()