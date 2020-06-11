#include "TMath.h"
#include "models.h"
#include "vdt/vdtMath.h"
#include <cmath>


double MyErfc(double x, double x0, double width) {
  return TMath::Erfc((x - x0) / width);
}
