function login() {
	var username = document.getElementById("inputEmail1").value;
	var password = document.getElementById("inputPassword1").value;
	

	// send to server
		$.ajax({
            url: apiUrl + 'login',
            type: 'POST',
			datatype: 'json',
			xhrFields: {
				withCredentials: true
			},
			// headers: {
				// 'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
				// 'Content-Type': 'application/x-www-form-urlencoded'
			// },
            data: {
				"email": username,
				"pw": password,
				"submit": "Daten+absenden"
			},
            success: function (data) {
				data = JSON.parse(data);
				console.log(data);
				
				if (data.hasOwnProperty("type") && data.hasOwnProperty("message") && data.type == "error") {
					document.getElementById("wrongPassword").style.display = "block";
				} else {
					setCookie("login", "true");
					setCookie("userid", data.message.userid);
					setCookie("isAdmin", data.message.isAdmin.toLowerCase());
//					setCookie("user", username, 5);
					// redirect to last visited page
					// var lastPage = getCookie("lastPage");
					// lastPage = lastPage.replace("logout=true&", "");
					var lang = getUrlVars()["lang"];
					// lastPage = lastPage.replace("logout=true", "");
					window.location.href = "index.html?lang=" + lang;
				}
				
            }
        });

	
}



function newAccount() {
	
	document.getElementById("pleaseEnter").style.display = "none";
	document.getElementById("newAccountSuccess").style.display = "none";
	document.getElementById("usernameNotAvailable").style.display = "none";
	document.getElementById("robotError").style.display = "none";
	document.getElementById("passwordNotEqual").style.display = "none";
	document.getElementById("otherError").style.display = "none";
	
	var username = document.getElementById("inputEmail2").value;
	var password = document.getElementById("inputPassword2").value;
	var password2 = document.getElementById("inputPassword3").value;
	var number = document.getElementById("inputCheck").value;
	
	if (username == null || username.length<1 || password == null || password.length<1) {
		document.getElementById("pleaseEnter").style.display = "block";
	} else {
		// send to server
		
			$.ajax({
            url: apiUrl + 'register',
            type: 'POST',
            data: {
				"email": username,
				"pw": password,
				"pw2": password2,
				"number": number,
				"submit": "Daten+absenden"
			},
            success: function (data) {
				data = JSON.parse(data);
				console.log(data);
				
				if (data.hasOwnProperty("type") && data.hasOwnProperty("message") && data.type == "error") {
					if (data.message == "User already exists with this email.") {
						document.getElementById("usernameNotAvailable").style.display = "block";
					} else if (data.message == "Passwords not equal.") {
						document.getElementById("passwordNotEqual").style.display = "block";
					} else if (data.message == "Are you a robot?") {
						document.getElementById("robotError").style.display = "block";
					} else if (data.message == "Could not create a user.") {
						document.getElementById("otherError").style.display = "block";
					}
				} else {
					// success
					document.getElementById("newAccountSuccess").style.display = "block";
				}
				
            }
        });
	}
	
}