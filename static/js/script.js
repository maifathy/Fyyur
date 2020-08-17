window.parseISOString = function parseISOString(s) {
  var b = s.split(/\D+/);
  return new Date(Date.UTC(b[0], --b[1], b[2], b[3], b[4], b[5], b[6]));
};
const btnDeleteVenue = document.querySelector("#btnDeleteVenue")
if(btnDeleteVenue !== null)
{
  btnDeleteVenue.addEventListener('click', function(e){
    let r = confirm("Are you sure you want to delete this venue?");
    if (r == true) {
      fetch('/venues/' + btnDeleteVenue.dataset["id"], {
        method: 'DELETE'
      })
      .then(function(){
          window.location.href = '/';
      }) 
    }                  
  });
}