function generateNotification(notifType, notifText){
    new Noty({
       type: notifType, //Valores posibles: alert, success, error, warning, info
       layout: 'topCenter',
       theme: 'nest',
       text: notifText,
       timeout: '4000',
       progressBar: true,
       closeWith: ['click'],
       killer: true,
    }).show();
}

/*
** Common methods to call SocketIO for the pages registerPatient, viewPatient, registerGroup and viewGroup
**/

//TODO: probably, these socketIO methods will be deleted after reviewing the whole code

//NEW PATTERN inserted on the accordion's formulary
function insertNewPattern(){

    var intensity1 = document.getElementById("patternIntensity1").checked ? 1 : 0;
    var intensity2 = document.getElementById("patternIntensity2").checked ? 1 : 0;
    var intensity3 = document.getElementById("patternIntensity3").checked ? 1 : 0;

    var body = document.getElementById("windowToken").value + "," + document.getElementById("patternName").value + "," + document.getElementById("patternDescription").value + "," + intensity1 + "," + intensity2 + "," + intensity3;


    socket.emit('insertNewPattern', body);
}

//GROUP select is changed
function changedSelectGroup(){
    socket.emit('changedSelectGroup', document.getElementById('windowToken').value + "," + $('#groupSelect').multipleSelect('getSelects'));
}

//PATTERN select is changed
function changedSelectPattern(){
    socket.emit('changedSelectPattern', document.getElementById('windowToken').value + "," + $('#patternsSelect').multipleSelect('getSelects'));
}

//--- Modal scripts ---//
        
function displayModalSave(){
    var modalDiv = document.getElementById("page-modal-save");
    modalDiv.style.display = "block";
}

function closeModalSave(){
    var modalDiv = document.getElementById("page-modal-save");
    modalDiv.style.display = "none";
}

function displayModalCancel(){
    var modalDiv = document.getElementById("page-modal-cancel");
    modalDiv.style.display = "block";
}

function closeModalCancel(){
    var modalDiv = document.getElementById("page-modal-cancel");
    modalDiv.style.display = "none";
}

function displayModalDelete(){
    var modalDiv = document.getElementById("page-modal-delete");
    modalDiv.style.display = "block";
}

function closeModalDelete(){
    var modalDiv = document.getElementById("page-modal-delete");
    modalDiv.style.display = "none";
}

function confirmSave(){
      document.getElementById("generalForm").submit();
  }

function cancelChanges(){
   window.location.href = window.location.href;
}