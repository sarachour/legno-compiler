if (!Object.prototype.watch) {
    Object.defineProperty(
        Object.prototype,
        "watch", {
            enumerable: false,
            configurable: true,
            writable: false,
            value: function (prop, handler) {
                var old = this[prop];
                var cur = old;
                var getter = function () {
                    return cur;
                };
                var setter = function (val) {
                    old = cur;
                    cur =
                        handler.call(this,prop,old,val);
                    return cur;
                };
                // can't watch constants
                if (delete this[prop]) {
                    Object.defineProperty(this,prop,{
                        get: getter,
                        set: setter,
                        enumerable: true,
                        configurable: true
                    });
                }
            }
        });
}

class APIManager {
    constructor(addr,port){
        this.addr = addr;
        this.port = port;
    }
    url(endpt){
        return endpt;
    }
    get_hidden_state(blk,inst,state,cbk){
        $.get(
            this.url("/hidden_states"),
            {"block":blk,
             "loc":inst,
             "static_state":state},
            function(data) {
                cbk(data['hidden_state']);
            }
        );
    }
    get_static_state(blk,inst,cbk){
        $.get(
            this.url("/static_states"),
            {"block":blk,
             "loc":inst},
            function(data) {
                cbk(data['static_state']);
            }
        );
    }
    get_instances(blk,cbk){
        $.get(
            this.url("/instances"),
            {"block":blk},
            function(data) {
                cbk(data['instances']);
            }
        );
    }
    get_blocks(cbk){
        $.get(
            this.url("/blocks"),
            {},
            function(data) {
                cbk(data['blocks']);
            }
        );
    }
}
class ModelView {
    constructor(model){
	      if(model == null){
            console.log(this);
	          console.log("model is null");
	      }
        this.model = model;
    }
    unbind(name){
        this.model.unwatch(name);
    }
    bind(name){
        this.model.watch(name, function(p,o,n){m.redraw();return n;});
    }
}


class BlockConfigModel {
    constructor(api){
        this.api = api;
        // currently selected
        this.block= null;
        this.instance = null;
        this.static_state = null;
        this.hidden_state = null;

        this.blocks = [];
        this.instances = [];
        this.static_states = [];
        this.hidden_states = [];

        var that = this;
        this.watch("block", function(p,o,new_val){
            if(o != new_val){
                that.instances = [];
                that.instance = null;
                that.get_instances(new_val);
            }
            return new_val;
        });
        this.watch("instance", function(p,o,new_val){
            if(o != new_val){
                that.static_states = [];
                that.static_state = null;
                that.get_static_states(new_val);
            }
            return new_val;
        });
        this.watch("static_state", function(p,o,new_val){
            console.log("static state updated",o,new_val);
            if(o != new_val){
                that.hidden_states = [];
                that.hidden_state = null;
                that.get_hidden_states(new_val);
            }
            return new_val;
        });

    }

    initialize(){
        var that = this;
        this.api.get_blocks(function(blocks){
            that.blocks = blocks;
        });
    }

    get_hidden_states(static_state){
        console.log("updating hidden state");
        if(static_state == null){
            this.hidden_states = [];
        }
        else{
            var that = this;
            this.api.get_hidden_state(this.block,
                                      this.instance,
                                      static_state,
                                      function(state){
                                          console.log(state);
                                          that.hidden_states = state;
                                      });
        }
    }


    get_static_states(instance){
        if(instance == null){
            this.static_states = [];
        }
        else{
            var that = this;
            this.api.get_static_state(this.block,
                                      instance,
                                      function(state){
                                          that.static_states = state;
                                      });
        }
    }

    get_instances(block){
        var that = this;
        if(block == null){
            this.instances = [];
        }
        else{
            this.api.get_instances(block,
                                function(insts){
                                    that.instances = insts;
                                });
        }
    }
}


class HiddenStateSelector extends ModelView {
    constructor(viewport,model){
        super(model);
        this.viewport = viewport;
        this.bind("hidden_states");
    }
    view(arg){
        var that = this;
        var update_hidden_state = function(args){
            console.log("update hidden state");
            if(args.target.value == 'null'){
                that.model.hidden_state = null;
            }
            else{
                that.model.hidden_state = args.target.value;
            }
        };
        var elems = [m("option",
                       {class:"no-select",
                        value:"null"},
                       "<select hidden code>")];
        this.model.hidden_states.forEach(function(hidden_cfg){
            elems.push(m("option", {class:'hidden-state',
                                    value:hidden_cfg}, hidden_cfg));
        });
        return m("select", {class:"hidden-state-selector",
                            onchange:update_hidden_state},
                 elems);
    }
}
class StaticStateSelector extends ModelView {
    constructor(viewport,model){
        super(model);
        this.viewport = viewport;
        this.bind("static_states");
    }
    view(arg){
        var that = this;
        var update_static_state = function(args){
            if(args.target.value == 'null'){
                that.model.static_state = null;
            }
            else{
                that.model.static_state = args.target.value;
            }
        };
        var elems = [];
        if(this.model.static_states.length > 0){
            this.model.static_states.forEach(function(static_cfg){
                elems.push(m("option", {class:'static-state',
                                        value:static_cfg}, static_cfg));
            });
        }
        else{
            elems.push([m("option",
                          {class:"no-select",
                           value:"null"},
                          "<select loc>")]);
        }
        update_static_state({'target':elems[0]});
        return m("select", {class:"static-state-selector",
                            onchange:update_static_state},
                 elems);
    }
}
class InstanceSelector extends ModelView {
    constructor(viewport,model){
        super(model);
        this.viewport = viewport;
        this.bind("instances");
    }
    view(arg){
        var that = this;
        var update_static_state = function(args){
            console.log("update instance");
            if(args.target.value == 'null'){
                that.model.instance = null;
            }
            else{
                that.model.instance = args.target.value;
            }
        };
        var elems = [m("option",
                       {class:"no-select",
                        value:"null"},
                       "<select loc>")];
        this.model.instances.forEach(function(loc){
            elems.push(m("option", {class:'instance',
                                    value:loc}, loc));
        });
        return m("select", {class:"instance-selector",
                            onchange:update_static_state},
                 elems);
    }
}
class BlockSelector extends ModelView {
    constructor(viewport,model){
        super(model);
        this.viewport = viewport;
        this.bind("blocks");
    }
    view(arg){
        var that = this;
        var update_block = function(args){
            console.log("update block");
            if(args.target.value == 'null'){
                that.model.block = null;
            }
            else{
                that.model.block = args.target.value;
            }
        };
        var elems = [m("option",
                       {class:"block",
                        value:"null"},
                       "<select block>")];
        this.model.blocks.forEach(function(blk){
            elems.push(m("option", {class:"block",
                                    value:blk}, blk));
        });
        return m("select", {class:"block-selector",
                            onchange:update_block},
                 elems);
    }
}

class Viewport {
    constructor(apis){
        this.api = api;
        this.model = new BlockConfigModel(api);
        this.model.initialize();
        this.block_selector = new BlockSelector(this,this.model);
        this.loc_selector = new InstanceSelector(this,this.model);
        this.static_state_selector = new StaticStateSelector(this,
                                                             this.model);
        this.hidden_state_selector = new HiddenStateSelector(this,
                                                             this.model);

    }
    view(arg){
        var that = arg.tag;
        return m(".viewport",
                 [
                     that.block_selector.view(that.block_selector),
                     that.loc_selector.view(that.loc_selector),
                     that.static_state_selector.view(that.static_state_selector),
                     that.hidden_state_selector.view(that.hidden_state_selector)
                 ]);
    }
}

/*
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

function get_sensitivity(datum){
    output_bounds = datum.bounds[datum.output];
    max_range = Math.max(Math.abs(output_bounds[0]),
              Math.abs(output_bounds[1]));

    sensitivity_frac = parseInt($("#sensitivity").val())/100.0;
    if(sensitivity_frac == 0){
        sensitivity_frac = 0.01;
    }
    return max_range*sensitivity_frac;

}

function get_error_function(){
    error_fn = $("#plot_func").val();
    if(error_fn == "reference"){
        return function(ref,pred,model,mean,std){
            return Math.abs(mean-ref);
        };
    }
    else if(error_fn == "prediction"){
        return function(ref,pred,model,mean,std){
            return Math.abs(mean-pred);
        };
    }
    else if(error_fn == "model"){
        return function(ref,pred,model,mean,std){
            return Math.abs(mean-model);
        };
    }
    else if(error_fn == "stdev"){
        return function(ref,pred,model,mean,std){
            return std;
        };
    }
    else{
        alert("unknown: "+ error_fn);
    }
}
function render_model_info(){
    var static_state =GLOBALS.static_state;
    var hidden_state = GLOBALS.hidden_state;
    var datum = GLOBALS.data[static_state][hidden_state];
    console.log(datum['info']);
    $("#model").html(datum['info']['model']);
    $("#correctable_model").html(datum['info']['correctable_model']);

}
function render_heatmap(){
    var static_state =GLOBALS.static_state;
    var hidden_state = GLOBALS.hidden_state;
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

    error_func = get_error_function();
    heatmap_data = [];
    datum.data.meas_mean.forEach(function(meas_val,idx){
        var ref_val = datum.data.outputs[idx];
        var meas_std = datum.data.meas_stdev[idx];
        var pred_val = datum.data.predict[idx];
        var delta_val = datum.data.delta_model[idx];
        var x = datum.data.inputs[xfield][idx];
        var y = 0.0;
        if(yfield != null){
            y = datum.data.inputs[yfield][idx];
        }
        var error = error_func(ref_val,
                               pred_val,pred_val,
                               meas_val,meas_std);
        heatmap_data.push(
            make_datapoint(datum,xfield,x,yfield,y,error)
        );
    });
    GLOBALS.heatmap_data = heatmap_data;
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
function update_heatmap(){
    render_heatmap(GLOBALS.hidden_state);
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
        GLOBALS.hidden_state = hidden_state;
        render_heatmap();
        render_model_info();
    });
    update_static_state(static_state);
}

function populate_blocks(){
    $.get(
        "blocks/",
        {''},
        function(data) {
            alert('page content: ' + data);
        }
    );
}

$(document).ready(function(){
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

    populate_blocks();
    $("#plot_funcs").on("change", function(){
        update_heatmap();
    });
    $("#sensitivity").on("change", function(){
        update_heatmap();
    });
})
*/
