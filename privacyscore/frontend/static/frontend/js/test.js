var resultColumns = ["Bewertung", "HTTPS", "Anzahl Cookies"];
var global_list_id = "";
var global_group = "";

$( document ).ready(function() {
	var listid = getUrlVars()["list"];
	var group = getUrlVars()["group"];
	var demo = getUrlVars()["demo"];
	global_group = group;
	var param = "";
	param = listid;
	if (listid != null && demo == null) {
		if (group != null) {
			param += "/" + group;
		}

	}         $.get("http://46.4.98.113:50080/ShowScannedList/" + param, function (jsonString) {
			//jsonString = jsonString.replace(/'/g, '"');
			data = JSON.parse(jsonString);
			//console.log(data);
			if (data == null) {
				document.getElementsByTagName("content").item(0).innerHTML = "<br>Fehler! Keine Liste mit der ID " + listid + " gefunden.";
			} else {
				callback(jsonString);
			}
        });
	
});

function demo(json) {
	data = JSON.parse(json);
	callback(data);
	
}

function callback(json){
	if (json == null) {
		document.getElementsByTagName("content").item(0).innerHTML = "<br>Fehler! Keine Liste mit der ID gefunden.";
	} else {
		document.getElementsByTagName("content").item(0).innerHTML = json;
		
		
	}
}