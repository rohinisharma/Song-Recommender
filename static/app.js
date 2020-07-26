var elements= document.getElementsByTagName('td');
for(var i=0; i<elements.length;i++)
{
(elements)[i].addEventListener("click", function(){
   alert(this.innerHTML);
});
}