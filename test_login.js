const axios = require('axios');
const FormData = require('form-data');

async function test() {
  try {
    const signupData = {
      email: `test_${Date.now()}@example.com`,
      password: "password",
      full_name: "Test User",
      role: "guest"
    };
    await axios.post('http://localhost:8000/v1/signup', signupData);
    
    // login
    let formData = new URLSearchParams();
    formData.append("username", signupData.email);
    formData.append("password", "password");

    const loginRes = await axios.post("http://localhost:8000/v1/login/access-token", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    
    console.log("Token:", loginRes.data.access_token);
    
    // fetch me
    const meRes = await axios.get("http://localhost:8000/v1/users/me", {
      headers: { Authorization: `Bearer ${loginRes.data.access_token}` }
    });
    console.log("Me:", meRes.status);
  } catch(e) {
    console.log("Error:", e.response ? e.response.status : e.message);
  }
}
test();
