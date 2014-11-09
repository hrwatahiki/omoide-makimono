$(document).ready(function() {
  $(".thumbnail-table").css({"display":"none"});
  $(this).delay(200).queue(function() {
    $(".thumbnail-list img").MyThumbnail({
      thumbWidth:100,
      thumbHeight:100,
      backgroundColor:"#ccc",
      imageDivClass:"myPic"
    });
    $(".thumbnail-table").css({"display":"table"});
    $(this).dequeue();
  });
});


