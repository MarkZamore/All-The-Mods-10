// priority: 1000
// ATM10 8.4 author workaround: keep Draconic Evolution's 3D HUD while using
// ImmediatelyFast's ordinary HUD submission instead of its batching path.
// Apply to the loaded native configuration only; preserve the player's file.
(() => {
  const ImmediatelyFast = Java.loadClass('net.raphimc.immediatelyfast.ImmediatelyFast')
  ImmediatelyFast.config.hud_batching = false
  ImmediatelyFast.runtimeConfig.hud_batching = false
})()
