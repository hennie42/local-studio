#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SpinActor.generated.h"

UCLASS()
class STUDIOGAME_API ASpinActor : public AActor
{
	GENERATED_BODY()

public:
	ASpinActor();
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spin")
	float DegreesPerSecond = 90.f;
};
