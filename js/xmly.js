console.log(document.querySelectorAll("div.sound-list a[href^='/']"))
highlightedItems = document.querySelectorAll("div.sound-list a[href^='/']")
var s = ""
highlightedItems.forEach((userItem) => {
  console.log(userItem.href)
  s+="bash xmlyfetcher 47995479 track "
  s+=userItem.href.split("/sound/")[1]
  s+="\n"
});
console.log(s)