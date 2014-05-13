/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

"use strict";

module.metadata = {
  "stability": "experimental"
};

const { Cu, Cc, Ci } = require("chrome");
const { Class } = require("../sdk/core/heritage");
const { Disposable } = require("../sdk/core/disposable");
const method = require("method/core");
const { contract, validate } = require("../sdk/util/contract");
const { each, pairs, values } = require("../sdk/util/sequence");

const { gDevTools } = Cu.import("resource:///modules/devtools/gDevTools.jsm", {});

// This is temporary workaround to allow loading of the developer tools client code
// into a toolbox panel before it lands.
const registerSDKURI = () => {
  const ioService = Cc['@mozilla.org/network/io-service;1']
                      .getService(Ci.nsIIOService);
  const resourceHandler = ioService.getProtocolHandler("resource")
                                   .QueryInterface(Ci.nsIResProtocolHandler);

  const uri = module.uri.replace("dev/toolbox.js", "");
  resourceHandler.setSubstitution("sdk", ioService.newURI(uri, null, null));
};

registerSDKURI();


const build = method("tool/build");
exports.build = build;

const Tool = Class({
  extends: Disposable,
  setup: function(params={}) {
    const { panels } = validate(this, params);

    this.panels = panels;

    each(([key, Panel]) => {
      const { url, label, tooltip, icon } = validate(Panel.prototype);
      const { id } = Panel.prototype;

      gDevTools.registerTool({
        id: id,
        url: "about:blank",
        label: label,
        tooltip: tooltip,
        icon: icon,
        isTargetSupported: target => target.isLocalTab,
        build: (window, toolbox) => build(Panel.prototype,
                                          window,
                                          toolbox,
                                          url)
      });
    }, pairs(panels));
  },
  dispose: function() {
    each(Panel => gDevTools.unregisterTool(Panel.prototype.id),
         values(this.panels));
  }
});

validate.define(Tool, contract({
  panels: {
    is: ["object", "undefined"]
  }
}));
exports.Tool = Tool;