$(document).ready(function(){$("#resetlnk").bind("click",function(a){a.preventDefault();$("#login_part").hide();$("#forgottenpw").show()});$("#cancelrset").bind("click",function(a){a.preventDefault();$("#forgottenpw").hide();$("#login_part").show()});$("#lang").change(function(){var b=$("#lang").val();var a={language:b,next:next+$("#loginform [name=next]").val(),csrfmiddlewaretoken:$("#loginform [name=csrfmiddlewaretoken]").val()};$.post(url,a,function(c){location.href=next+$("#loginform [name=next]").val()})});$("html").ajaxSend(function(){$("#login").attr("disabled","disabled")}).ajaxStop(function(){$("#login").removeAttr("disabled")})});