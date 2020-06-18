
GLOBALS = {
    data:null,
    static_state:null,
    hidden_state:null,
    heatmap:null,
    width:0,
    height:0
};

function make_datapoint(datum,vx,x,vy,y,value){
    datum['bounds'][null] = [0,1];
    var xbound = datum['bounds'][vx];
    var ybound = datum['bounds'][vy];
    var px_delta = GLOBALS.width/(xbound[1]-xbound[0]);
    var py_delta = GLOBALS.height/(ybound[1]-ybound[0]);
    var px_center = Math.round(-xbound[0]*px_delta);
    var py_center = Math.round(-ybound[0]*py_delta);
    var px = Math.round(x*px_delta) + px_center;
    var py = Math.round(y*py_delta) + py_center;
    d = {x:px, y:py, value:value};
    console.log(d);
    return d;

}
function change_heatmap_settings(){
    
}
function get_sensitivity(datum){
    return 0.5;
}
function render_heatmap(hidden_state){
    var static_state =GLOBALS.static_state;
    GLOBALS.hidden_state = hidden_state;
    var datum = GLOBALS.data[static_state][hidden_state];
    input_keys = [null,null];
    idx = 0;
    console.log(datum.data.inputs);
    for(let [input,d] of Object.entries(datum.data.inputs)){
        input_keys[idx] = input;
        idx += 1;
    }
    xfield = input_keys[0];
    yfield = input_keys[1];

    heatmap_data = [];
    datum.data.meas_mean.forEach(function(meas_val,idx){
        var ref_val = datum.data.outputs[idx];
        var pred_val = datum.data.predict[idx];
        var x = datum.data.inputs[xfield][idx];
        var y = 0.0;
        if(yfield != null){
            y = datum.data.inputs[yfield][idx];
        }
        var error = Math.abs(meas_val-ref_val);
        heatmap_data.push(
            make_datapoint(datum,xfield,x,yfield,y,error)
        );
    });
    console.log(heatmap_data);
    GLOBALS.heatmap_data = heatmap_data
    GLOBALS.heatmap.setData({
        max: get_sensitivity(datum),
        data: heatmap_data
    });
    $("#xfield").html(xfield);
    $("#yfield").html(yfield);
    GLOBALS.heatmap.configure({
        xField: xfield,
        yField: yfield
    });
}
function update_static_state(static_state){
    GLOBALS.static_state = static_state;
    selector = $("#hidden_state");
    selector.empty();
    for(hidden in GLOBALS.data[static_state]){
        selector.append(new Option(hidden,hidden));
    }
}

function build_ux(data){
    GLOBALS.data = data;
    static_selector = $("<select>");
    static_selector.attr("id","static_state");
    for(static_state in data){
        static_selector.append(new Option(static_state,
                                          static_state));
    }
    $("#block_state").append("static:");
    $("#block_state").append(static_selector);
    hidden_selector = $("<select>");
    hidden_selector.attr("id","hidden_state");
    $("#block_state").append("hidden:");
    $("#block_state").append(hidden_selector);

    $("#static_state").on("change",function(obj){
        var static_state = obj.target.value;
        update_static_state(static_state);
    });
    $("#hidden_state").on("change",function(obj){
        var hidden_state = obj.target.value;
        render_heatmap(hidden_state);
    });
    console.log(static_selector.value);
    update_static_state(static_state);
}

function upload_file(filename){
    var reader = new FileReader();
    reader.onload = (function(thefile){
        return function(e){
            text = e.target.result;
            obj = JSON.parse(text);
            console.log(obj);
            build_ux(obj);
        };
    })(filename);
    reader.readAsText(filename);
}

$(document).ready(function(){
    $("#data_upload").on("change",function(){
        var files = this.files;
        var filename = files[0];
        upload_file(filename);
    });

    heatmap_container = document 
        .querySelector("#profile_vis");
    heatmap_container.style.width = "500px";
    heatmap_container.style.height = "500px";
    GLOBALS.width = 500;
    GLOBALS.height = 500;
    GLOBALS.heatmap = h337.create({
        container: heatmap_container,
        backgroundColor:"black"
    });
})
