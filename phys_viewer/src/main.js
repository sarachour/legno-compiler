
function build_ux(data){
    static_state = [];
    hidden_state = {};
    for(static_values in data){
        static_state.push(static_values);
        for(hidden in data[static_values]){
            datum = data[static_values][hidden];
            for(st_name in datum["config"]["stmts"]){
                st = datum["config"]["stmts"][st_name];
                if(st['type'] == "state"){
                    if(!(st['name'] in hidden_state)){
                        hidden_state[st['name']] = [];
                    }
                    if(hidden_state[st['name']].indexOf(st['value']) < 0){
                        hidden_state[st['name']].push(st['value']);
                    }
                }
            }
        }
    }
    mode_selector = $("<select>");
    for(idx in static_state){
        mode = static_state[idx];
        mode_selector.append(new Option(mode, mode));
    }
    $("#block_state").append("mode:");
    $("#block_state").append(mode_selector);

    for(hidden in hidden_state){
        values = hidden_state[hidden];
        hidden_selector = $("<select>");
        hidden_selector.attr('id',"#"+hidden);
        values.forEach(function(idx,val){
            hidden_selector.append(new Option(val,val));
        });
        $("#block_state").append(hidden+":");
        $("#block_state").append(hidden_selector);
    }
    console.log(static_state);
    console.log(hidden_state);
}
function upload_file(obj){
    var files = obj.files;
    filename = files[0];
    var reader = new FileReader();

    reader.onload = (function(thefile){
        return function(e){
            text = e.target.result;
            obj = JSON.parse(text);
            build_ux(obj);
        };
    })(filename);
    reader.readAsText(filename);

    console.log(obj);
}
$(document).ready(function(){
    console.log("test");
    $("#data_upload").on("change",function(){
        upload_file(this);
    });
    build_ux(DATA);
})
