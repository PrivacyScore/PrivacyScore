var langData;

$( document ).ready(function() {
	var lang = getUrlVars()["lang"];
	if (lang == null) {
		lang = "de";
	}
	
	// if logged in, show the own list button
	var loggedIn = getCookie("login");
	if (loggedIn != null && loggedIn == "true") {
		document.getElementById("privateSearchButton").style.display = "inline";
	}
	
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (data) {
		langData = data;
		$.get(apiUrl + "/ShowLists/", function (jsonString) {
			var data = jsonString;
			callback(data, null, false);
		});
	});

});

function searchButton() {
	var text = document.getElementById("searchForm").value;
	if (text.length<1) {
		$.get(apiUrl + "/ShowLists/", function (jsonString) {
			var data = jsonString;
			callback(data, null, false);
		});
	} else {
		$.ajax({
				url: apiUrl + '/Search/',
				type: 'POST',
				data: {
					'searchtext': text
					// 'options': {
						// 'name': 1,
						// 'description': 1,
						// 'tags': 1
					// }
				},
				// headers: {
					// 'Content-Type': 'application/json; charset=utf-8;'
				// },
				success: function (data) {
					console.log(data);
					var json = data;
					callback(json, text, false);
				}
			});
	}
}


function callback(json, searchText, isOwnList){
	document.getElementById("privateSearch").style.display = "none";
	document.getElementById("search").style.display = "block";
	var lang = getUrlVars()["lang"];
	if (lang == null || lang.length<1) {
		lang = "de";
	}
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (data) {
		console.log(json);
		setSearchResults(sortResults(json), data.browse, isOwnList);
		if (searchText != null && searchText.length>0) {
			setSearch(data.browse.searchResults, searchText);
		}
	});

  	//setPopularLists(json.popularLists);
	//setNewLists(json.newLists);
  
}

function sortResults(json) {
	// push all timestamps to an array
	var timestamps = [];
	for (var i=0; i<json.length; i++) {
		if (json[i].scangroups.length>0) {
			var length = json[i].scangroups.length;
			var date = new Date(json[i].scangroups[length-1].startdate);
			var unix = Date.parse(date.toString());
			timestamps.push(unix);
		} else {
			timestamps.push(1);
		}
	}
		
	// create an array with indizes sorted by their timestamps
	var sortedIndex = [];
	for (var iteration=0; iteration<timestamps.length; iteration++) {
		var min = 0;
		var iterationIndex = 0;
		for (var i=0; i<timestamps.length; i++) {
			if ((sortedIndex.indexOf(i) == -1) && (timestamps[i] >= min)) {
				min = timestamps[i];
				iterationIndex = i;
			}
		}
		sortedIndex.push(iterationIndex);
	}
	
	//create the sorted array of results
	var sortedJson = [];
	for (var i=0; i<sortedIndex.length; i++) {
		sortedJson.push(json[sortedIndex[i]]);
	}
	return sortedJson;
}

function setSearchResults(searchResults, lang, isOwnList) {
	var html = '';
	
	if (searchResults.length > 0) {
		for (var i=0; i<searchResults.length; i++) {
			html += '<li class="well well-lg" style="display:block;list-style-type: none">';
			html += '<h4>';
			var length = searchResults[i].scangroups.length - 1;
				if (length>0 || (length==0 && searchResults[i].scangroups[length].state == "finish")) {
				html += ' <a href="scannedList.html?lang=' + langData.lang + '&list=';
				html += searchResults[i].id;
				if (searchResults[i].scangroups.length>0) {
					html += "&group=";
					var length = searchResults[i].scangroups.length - 1;
					if (searchResults[i].scangroups[length].state == "finish") {
						html += searchResults[i].scangroups[length].id;
					} else if (searchResults[i].scangroups.length > 1) {
						html += searchResults[i].scangroups[length-1].id;
					}
				}
				html += '">';
				} else if (length==0 && searchResults[i].scangroups[length].state != "finish") {
					html += ' <a href="scannedList.html?lang=' + langData.lang + '&list=';
					html += searchResults[i].id;
					html += '">';
					html += searchResults[i].name;
					html += '</a>';
				} else if (searchResults[i].editable) {
					html += ' <a href="list.html?lang=' + langData.lang + '&listid=';
					html += searchResults[i].id;
					html += '">';
				}

			if (length>0 || (length==0 && searchResults[i].scangroups[length].state == "finish")) {
				html += searchResults[i].name;
				html += ' <i class="fa fa-arrow-circle-o-right"></i>';
				html += '</a>';
			} else if (searchResults[i].editable) {
				html += searchResults[i].name;
				html += ' <i class="fa fa-cog"></i>';
				html += '</a>';
			}
			// add the delete button if isOwnList
			if (isOwnList) {
				html += '<i class="fa fa-trash" style="margin-left:20px;" data-toggle="tooltip" title=' + "'" + lang.tooltipDelete + "'" + ' onclick="deleteList(' + "'" + searchResults[i].id + "'" + ')"></i>';
			}
			html += '<span style="float:right;"><span class="glyphicon glyphicon-time" data-toggle="tooltip" title="' + lang.tooltips[2] + '"></span> ';
			var length = searchResults[i].scangroups.length - 1;
			if (searchResults[i].scangroups.length>0 && searchResults[i].scangroups[length].state == "finish") {
				var date = getDate(searchResults[i].scangroups[length].startdate, langData.timeFormat, langData.dateFormat);
				html += date;
			} else if (searchResults[i].scangroups.length>0 && searchResults[i].scangroups[length].state == "scanning") {
				if (searchResults[i].scangroups.length>1 && searchResults[i].scangroups[length-1].state == "finish") {
					// case: newest scan is scanning but there is an earlier scan that is finished
					var date = getDate(searchResults[i].scangroups[length-1].startdate, langData.timeFormat, langData.dateFormat);
					html += date;
					html += '<br><small><i class="fa fa-angle-double-right"></i> ' + langData.browse.progress.scanning + '</small>';
				} else {
					if (searchResults[i].scangroups.length==1) {
						html += langData.browse.progress.scanning;
						var date = getDate(searchResults[i].scangroups[0].startdate, langData.timeFormat, langData.dateFormat);
						html += '<br><small>Start: ';
						html += date;
						html += '</small>';
					} else {
						html += langData.browse.progress.scanning;
					}
				}
			} else if (searchResults[i].scangroups.length>0 && searchResults[i].scangroups[length].state == "ready") {
				if (searchResults[i].scangroups.length>1 && searchResults[i].scangroups[length-1].state == "finish") {
					// case: newest scan is ready but there is an earlier scan that is finished
					var date = getDate(searchResults[i].scangroups[length-1].startdate, langData.timeFormat, langData.dateFormat);
					html += date;
					html += '<br><small><i class="fa fa-angle-double-right"></i> ' + langData.browse.progress.scanning + '</small>';
				} else {
					html += langData.browse.progress.notScanned;
				}
			} else if (searchResults[i].scangroups.length>0 && searchResults[i].scangroups[length].state.indexOf("error")>-1) {
				if (searchResults[i].scangroups.length>1 && searchResults[i].scangroups[length-1].state == "finish") {
					// case: newest scan is error but there is an earlier scan that is finished
					var date = getDate(searchResults[i].scangroups[length-1].startdate, langData.timeFormat, langData.dateFormat);
					html += date;
				} else {
					html += langData.browse.progress.error;
				}
			}
			html += '</span></span>';
			html += '</h4>';
			if (searchResults[i].isprivate) {
				html += '<div><span class="glyphicon glyphicon-sunglasses"></span> ' + langData.browse.privateList;
				html += ' <i class="fa fa-globe" style="margin-left:5px; cursor: pointer;" onclick="setPublic(' + "'" + searchResults[i].id + "'" + ')"></i>';
				html += '<small> ' + langData.browse.setPublicDiv + '</small>';
				html += '</div>';
			}
			html += '<div style="margin-top:10px;">';
			html += '<span class="glyphicon glyphicon-info-sign" data-toggle="tooltip" title="' + lang.tooltips[0] + '"></span> '
			html += searchResults[i].description;
			html += '</div>';
			html += '<div style="margin-top:10px;">';
			html += '<span class="glyphicon glyphicon-tags" data-toggle="tooltip" title="' + lang.tooltips[1] + '"></span> ';
			html += searchResults[i].tags.toString().replace(/,/g,", ");
			html += '</div>';
			html += '</li>';
		}
	} else {
		html += langData.browse.noResults;
	}
	document.getElementById("searchResults").innerHTML = html;
	document.getElementById("searchResults").parentElement.style.marginBottom = "60px";
}

function getPopularNewLists(popularLists) {
	var html = '';
	for (var i=0; i<popularLists.length; i++) {
		html += '<ul>'
		html += '<li style="list-style-type: none;" class="list-group-item">';
		html += '<div class="newPopular" onclick="goToScan(';
		html += "'";
		html += popularLists[i].id;
		html += "'";
		html += ')">';
		html += popularLists[i].name;
		html += '</li>';
		html += '</div>';
		html += '</ul>'
	}
	return html;
}

function setPopularLists(popularLists) {
	var html = getPopularNewLists(popularLists);
	document.getElementById("popularLists").innerHTML = html;
}

function setNewLists(newLists) {
	var html = getPopularNewLists(newLists);
	document.getElementById("newLists").innerHTML = html;
}

function setSearch(langText, text) {
	var html = langText.replace("#VALUE", text);
	document.getElementById('search').innerHTML = html;
}

function goToScan(list) {
	var group = "";
	$.get(apiUrl + "GetScanGroups/" + list, function (jsonString) {
		//jsonString = jsonString.replace(/'/g, '"');
		data = jsonString;
		if (data != null) {
			var max = 0;
			for (var i=0; i<data.length; i++) {
				var date = new Date(data[i].startdate);
				var unix = Date.parse(date.toString());
				if (unix > max) {
					max = unix;
					group = data[i].id;
				}
			}
			window.location.href = './scannedList.html?lang=' + langData.lang + '&list=' + list + "&group=" + group;
		}
	});
}

function privateSearchButton() {
	
	$.ajax({
            url: apiUrl + '/getlist',
            type: 'GET',
			xhrFields: {
				withCredentials: true
			},
            success: function (data) {
				data = data;
				console.log(data);
				callback(data, null, true);
				document.getElementById("privateSearch").style.display = "block";
				document.getElementById("search").style.display = "none";
				document.getElementById("privateSearchButtonBack").style.display = "inline";
				
            }
        });
}

function privateSearchButtonBack() {
	document.getElementById("privateSearchButtonBack").style.display = "none";
	$.get(apiUrl + "/ShowLists/", function (jsonString) {
		var data = jsonString;
		callback(data, null, false);
	});
}

function setPublic(listid) {
	console.log(listid);
	
	$.ajax({
            url: apiUrl + '/setlist',
            type: 'POST',
			data: {
				"listid": listid,
				"action": "setPublic"
			},
			xhrFields: {
				withCredentials: true
			},
            success: function (data) {
				data = data;
				if (data.hasOwnProperty("type") && data.type == "success") {
					alert(langData.browse.setPublicSuccess);
				} else {
					alert("Error");
				}
				
            }
        });
}



function deleteList(listid) {
	if (confirm(langData.list.confirms.deleteList)) {
			$.ajax({
				url: apiUrl + '/GetToken/' + listid,
				type: 'POST',
				xhrFields: {
					withCredentials: true
				},
				success: function (data) {
					data = data;
				$.get(apiUrl + "/DeleteList/" + data.token + '/', function (jsonString) {
					var data = jsonString;
					console.log(data);
					var lang = getUrlVars()["lang"];
					window.location.href = "index.html?lang=" + lang;
					
				});
				}
			});
		
		
		
	} else {
		//alert("Die Liste wurde nicht gelöscht.");
		alert(langData.list.alerts.notDeleted);
	}
}
