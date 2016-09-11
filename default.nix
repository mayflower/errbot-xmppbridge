with import <nixpkgs> {};

stdenv.mkDerivation rec {
  name = "errbot-xmppbridge-${version}";
  version = "0.1.0";

  src = ./.;

  postUnpack = ''
    # Clean up when building from a working tree.
    if [[ -d $sourceRoot/.git ]]; then
      ${git}/bin/git -C $sourceRoot clean -fdx
    fi
  '';

  dontBuild = true;

  installPhase = ''
    mkdir -p $out
    cp xmppbridge.{py,plug} $out
  '';
}
