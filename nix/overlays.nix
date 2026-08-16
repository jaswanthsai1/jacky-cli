# nix/overlays.nix — Expose pkgs.jacky-agent for external NixOS configs
{ inputs, ... }:
{
  flake.overlays.default = final: _: {
    jacky-agent = final.callPackage ./jacky-agent.nix {
      inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
      npm-lockfile-fix = inputs.npm-lockfile-fix.packages.${final.stdenv.hostPlatform.system}.default;
      rev = inputs.self.rev or null;
    };
  };
}
